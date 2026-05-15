from __future__ import annotations

from dataclasses import asdict, dataclass
import re
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
    return [asdict(triage_ticket(_coerce_ticket(ticket))) for ticket in tickets]


def triage_ticket(ticket: Ticket) -> TriageResult:
    text = f"{ticket.subject} {ticket.description}".lower()
    category, category_hits = _classify_category(text)
    signals = _detect_signals(text, ticket.affected_users, category)
    priority = _priority(text, ticket.affected_users, category)
    redactions = _redactions(f"{ticket.subject} {ticket.description} {ticket.requester}")
    confidence = _confidence(category_hits, signals, redactions)

    return TriageResult(
        ticket_id=ticket.ticket_id,
        category=category,
        priority=priority,
        routing_group=ROUTES[category],
        sla_minutes=SLA_MINUTES[priority],
        confidence=confidence,
        signals=signals,
        redactions=redactions,
        suggested_response=_response(ticket, category, priority),
    )


def _coerce_ticket(ticket: dict | Ticket) -> Ticket:
    if isinstance(ticket, Ticket):
        return ticket
    return Ticket(
        ticket_id=str(ticket.get("ticket_id", ticket.get("id", "UNKNOWN"))),
        subject=str(ticket.get("subject", "")),
        description=str(ticket.get("description", "")),
        requester=str(ticket.get("requester", "unknown")),
        affected_users=int(ticket.get("affected_users", 1) or 1),
    )


def _classify_category(text: str) -> tuple[str, int]:
    scores = {
        category: sum(1 for keyword in keywords if keyword in text)
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
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
    if any(term in text for term in ("down", "outage", "unavailable", "cannot work")):
        signals.append("service_impact")
    if any(term in text for term in ("ransomware", "breach", "compromised", "phishing")):
        signals.append("security_incident")
    if any(term in text for term in ("ceo", "chief", "executive", "director")):
        signals.append("executive_request")
    if "ransomware" in text:
        signals.append("ransomware")
    return signals or ["needs_review"]


def _priority(text: str, affected_users: int, category: str) -> str:
    if category == "security" and any(term in text for term in ("ransomware", "breach", "compromised")):
        return "P1"
    if affected_users >= 50 or "outage" in text or "down" in text:
        return "P1"
    if category == "security" or affected_users >= 10 or "executive" in text:
        return "P2"
    if any(term in text for term in ("cannot work", "blocked", "urgent")):
        return "P2"
    if category in {"identity", "network", "cloud"}:
        return "P3"
    return "P4"


def _redactions(text: str) -> list[str]:
    checks = {
        "email": r"\b[\w.\-+]+@[\w.\-]+\.\w+\b",
        "phone": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "possible_secret": r"(?i)\b(password|token|secret|api[_-]?key)\s*[:=]\s*\S+",
    }
    return [label for label, pattern in checks.items() if re.search(pattern, text)]


def _confidence(category_hits: int, signals: list[str], redactions: list[str]) -> float:
    score = 0.55 + min(category_hits, 4) * 0.08 + min(len(signals), 4) * 0.04
    if redactions:
        score += 0.03
    return round(min(score, 0.98), 2)


def _response(ticket: Ticket, category: str, priority: str) -> str:
    route = ROUTES[category]
    return (
        f"We have classified this as a {priority} {category} ticket and routed it to "
        f"{route}. Please avoid sharing passwords or sensitive data in the ticket. "
        f"A technician will review ticket {ticket.ticket_id} within the SLA window."
    )

