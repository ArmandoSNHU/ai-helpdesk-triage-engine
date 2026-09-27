from __future__ import annotations

from dataclasses import asdict, dataclass
import re
import hmac
import secrets
from typing import Iterable


CATEGORY_KEYWORDS = {
    "identity": {
        "password",
        "locked",
        "login",
        "mfa",
        "duo",
        "account",
        "reset",
        "sign in",
        "sign-in",
    },
    "endpoint": {
        "laptop",
        "desktop",
        "printer",
        "keyboard",
        "monitor",
        "slow",
        "bsod",
        "crash",
        "windows",
    },
    "network": {
        "wifi",
        "wi-fi",
        "vpn",
        "network",
        "latency",
        "packet",
        "dns",
        "dhcp",
        "internet",
    },
    "security": {
        "phishing",
        "malware",
        "ransomware",
        "suspicious",
        "compromised",
        "breach",
        "virus",
        "unauthorized",
    },
    "software": {
        "application",
        "app",
        "license",
        "install",
        "update",
        "browser",
        "office",
        "teams",
    },
    "cloud": {
        "azure",
        "aws",
        "entra",
        "m365",
        "sharepoint",
        "onedrive",
        "tenant",
        "cloud",
    },
    "facilities": {
        "badge",
        "door",
        "access card",
        "camera",
        "room",
        "building",
    },
}

ROUTES = {
    "identity": "Identity and Access Management",
    "endpoint": "Desktop Support",
    "network": "Network Operations",
    "security": "Security Operations",
    "software": "Application Support",
    "cloud": "Cloud Operations",
    "facilities": "Facilities Support",
    "general": "Service Desk",
}

MAX_TICKETS = 1000
MAX_TEXT_LENGTH = 10000
MAX_ID_LENGTH = 256
MAX_AFFECTED_USERS = 1000000
# Ephemeral keyed references avoid exposing IDs or guessable plain ID hashes.
_ID_KEY = secrets.token_bytes(32)

SLA_MINUTES = {"P1": 15, "P2": 60, "P3": 240, "P4": 1440}


@dataclass(frozen=True)
class Ticket:
    ticket_id: str
    subject: str
    description: str
    requester: str = "unknown"
    affected_users: int = 1


@dataclass(frozen=True)
class TriageResult:
    ticket_id: str
    category: str
    priority: str
    routing_group: str
    sla_minutes: int
    confidence: float
    signals: list[str]
    redactions: list[str]
    suggested_response: str


def triage_tickets(tickets: Iterable[dict | Ticket]) -> list[dict]:
    if isinstance(tickets, (str, bytes, dict)):
        raise ValueError("Invalid ticket input.")
    try:
        iterator = iter(tickets)
    except TypeError:
        raise ValueError("Invalid ticket input.") from None
    results = []
    for index, ticket in enumerate(iterator):
        if index >= MAX_TICKETS:
            raise ValueError("Invalid ticket input.")
        results.append(asdict(triage_ticket(_coerce_ticket(ticket))))
    return results


def triage_ticket(ticket: Ticket) -> TriageResult:
    ticket = _coerce_ticket(ticket)
    text = f"{ticket.subject} {ticket.description}".lower()
    category, category_hits = _classify_category(text)
    signals = _detect_signals(text, ticket.affected_users, category)
    priority = _priority(text, ticket.affected_users, category)
    redactions = _redactions(f"{ticket.ticket_id} {ticket.subject} {ticket.description} {ticket.requester}")
    confidence = _confidence(category_hits, signals, redactions)

    return TriageResult(
        ticket_id="anon-" + hmac.new(_ID_KEY, ticket.ticket_id.encode("utf-8"), "sha256").hexdigest(),
        category=category,
        priority=priority,
        routing_group=ROUTES[category],
        sla_minutes=SLA_MINUTES[priority],
        confidence=confidence,
        signals=signals,
        redactions=redactions,
        suggested_response=_response(category, priority),
    )


def _coerce_ticket(ticket: dict | Ticket) -> Ticket:
    if isinstance(ticket, dict):
        ticket = Ticket(
            ticket_id=ticket.get("ticket_id", ticket.get("id", "UNKNOWN")),
            subject=ticket.get("subject", ""),
            description=ticket.get("description", ""),
            requester=ticket.get("requester", "unknown"),
            affected_users=ticket.get("affected_users", 1),
        )
    if not isinstance(ticket, Ticket):
        raise ValueError("Invalid ticket input.")
    for value, limit in ((ticket.ticket_id, MAX_ID_LENGTH), (ticket.subject, MAX_TEXT_LENGTH),
                         (ticket.description, MAX_TEXT_LENGTH), (ticket.requester, MAX_TEXT_LENGTH)):
        if not isinstance(value, str) or len(value) > limit:
            raise ValueError("Invalid ticket input.")
        # Reject invalid Unicode before encoding IDs or writing JSON.
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ValueError("Invalid ticket input.")
    if type(ticket.affected_users) is not int or not 0 <= ticket.affected_users <= MAX_AFFECTED_USERS:
        raise ValueError("Invalid ticket input.")
    return ticket


# Explicit forms avoid broad stemming (for example, "down" must not match "download").
PLURAL_FORMS = {
    word: word + "s"
    for word in (
        "password", "login", "account", "reset", "laptop", "desktop", "printer",
        "keyboard", "monitor", "network", "packet", "application", "app", "license",
        "install", "update", "browser", "tenant", "cloud", "badge", "door",
        "access card", "camera", "room", "building", "outage", "executive", "director",
    )
}
PLURAL_FORMS.update({"crash": "crashes", "breach": "breaches", "virus": "viruses", "chief": "chiefs"})


def _matches(text: str, term: str) -> bool:
    forms = (term, PLURAL_FORMS[term]) if term in PLURAL_FORMS else (term,)
    patterns = [r"\s+".join(re.escape(part) for part in form.split()) for form in forms]
    return re.search(r"(?<!\w)(?:" + "|".join(patterns) + r")(?!\w)", text, re.IGNORECASE) is not None


def _classify_category(text: str) -> tuple[str, int]:
    scores = {
        category: sum(1 for keyword in keywords if _matches(text, keyword))
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    # Any bounded security indicator takes precedence over competing category counts.
    if scores["security"]:
        return "security", scores["security"]
    category, hits = max(scores.items(), key=lambda item: item[1])
    if hits == 0:
        return "general", 0
    return category, hits


def _detect_signals(text: str, affected_users: int, category: str) -> list[str]:
    signals: list[str] = []
    if category != "general":
        signals.append(category)
    if affected_users >= 25:
        signals.append("multiple_users")
    if any(_matches(text, term) for term in ("down", "outage", "unavailable", "cannot work")):
        signals.append("service_impact")
    if any(_matches(text, term) for term in ("ransomware", "breach", "compromised", "phishing")):
        signals.append("security_incident")
    if any(_matches(text, term) for term in ("ceo", "chief", "executive", "director")):
        signals.append("executive_request")
    if _matches(text, "ransomware"):
        signals.append("ransomware")
    return signals or ["needs_review"]


def _priority(text: str, affected_users: int, category: str) -> str:
    if category == "security" and any(_matches(text, term) for term in ("ransomware", "breach", "compromised")):
        return "P1"
    if affected_users >= 50 or _matches(text, "outage") or _matches(text, "down"):
        return "P1"
    if category == "security" or affected_users >= 10 or _matches(text, "executive"):
        return "P2"
    if any(_matches(text, term) for term in ("cannot work", "blocked", "urgent")):
        return "P2"
    if category in {"identity", "network", "cloud"}:
        return "P3"
    return "P4"


def _redactions(text: str) -> list[str]:
    checks = {
        "email": r"\b[\w.\-+]+@[\w.\-]+\.\w+\b",
        "phone": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "possible_secret": r"(?i)\b(?:(?:password|passwd|token|secret|api[_-]?key)\s*[:=]\s*\S+|authorization\s*:\s*(?:bearer|basic)\s+\S+)",
    }
    return [label for label, pattern in checks.items() if re.search(pattern, text)]


def _confidence(category_hits: int, signals: list[str], redactions: list[str]) -> float:
    score = 0.55 + min(category_hits, 4) * 0.08 + min(len(signals), 4) * 0.04
    if redactions:
        score += 0.03
    return round(min(score, 0.98), 2)


def _response(category: str, priority: str) -> str:
    route = ROUTES[category]
    return (
        f"We have classified this as a {priority} {category} ticket and routed it to "
        f"{route}. Please avoid sharing passwords or sensitive data in the ticket. "
        "A technician will review this ticket within the SLA window."
    )

