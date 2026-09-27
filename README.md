# AI Helpdesk Triage Engine

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Use Case](https://img.shields.io/badge/Use%20Case-IT%20Helpdesk%20Automation-2563eb)](#what-it-does)
[![Tests](https://img.shields.io/badge/Tests-unittest-success)](#verification)

AI Helpdesk Triage Engine is a portfolio-ready ticket classification system for IT support queues. It turns raw helpdesk tickets into structured routing decisions with priority, confidence, SLA target, detected signals, data-redaction notes, and a suggested analyst response.

Classification is deterministic and runs locally without an API key. Output ticket references are pseudonymous and change when the Python process restarts.

## What It Does

- Classifies tickets into categories such as identity, endpoint, network, security, software, cloud, and facilities.
- Assigns priority from P1 to P4 using impact, urgency, and security indicators.
- Recommends a routing group and SLA target.
- Detects sensitive values such as email addresses, phone numbers, IP addresses, and possible secrets.
- Produces a support-ready response template.
- Supports JSON input/output for integration with service desk tools.

## Quick Start

```powershell
python -m ai_helpdesk_triage data\sample_tickets.json
```

Pretty-print the result:

```powershell
python -m ai_helpdesk_triage data\sample_tickets.json --pretty
```

Run tests:

```powershell
python -m unittest discover
```

## Example Output

Illustrative output; the 64 hexadecimal characters after `anon-` vary by process.

```json
{
  "ticket_id": "anon-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "category": "security",
  "priority": "P1",
  "routing_group": "Security Operations",
  "sla_minutes": 15,
  "confidence": 0.90,
  "signals": ["security", "multiple_users", "security_incident", "ransomware"],
  "redactions": ["email", "ip_address"],
  "suggested_response": "We have classified this as a P1 security ticket and routed it to Security Operations. Please avoid sharing passwords or sensitive data in the ticket. A technician will review this ticket within the SLA window."
}
```

## Repository Structure

```text
ai-helpdesk-triage-engine/
├── ai_helpdesk_triage/
│   ├── cli.py
│   └── engine.py
├── data/
│   └── sample_tickets.json
├── tests/
│   └── test_engine.py
├── pyproject.toml
├── README.md
└── codex.md
```

## Design Notes

The engine deliberately separates classification logic from CLI handling. That keeps the core triage contract reusable for a future REST API, queue consumer, ServiceNow export, or LLM-backed classifier.

Keyword matching uses whole words and phrases with explicit common plural forms.
Any security keyword takes routing precedence; ransomware, breach and compromised
indicators receive P1. Other security keywords receive at least P2. This is a
conservative keyword policy: negation such as `no ransomware` still escalates.
`confidence` is a heuristic score, not a probability. The `redactions` field only
reports detected data types and does not sanitize the original ticket.

## Input and output safety

Results never echo raw IDs, subjects, descriptions or requester values. `ticket_id`
is now an `anon-` reference derived with HMAC-SHA256 and a random process-local
key; equal IDs share a reference only within that process. This is a compatibility
change: consumers must correlate batch results by input order, rather than joining
on raw IDs. No key or ID mapping is saved. These references do not make the
classification or its context anonymous, and must not be used as authentication.

Input must be a JSON array of at most 1,000 ticket objects. Text fields must be
strings (ID: at most 256 characters; subject, description and requester: 10,000
characters each). `affected_users` must be an integer from 0 to 1,000,000, excluding
booleans. Missing fields retain defaults; explicit nulls and numeric strings are
rejected. Unknown fields are ignored. The CLI reads at most 2,000,000 bytes and
returns exit 2 with a generic JSON error for invalid files or input, without
echoing ticket values, paths or tracebacks. The library raises generic ValueError
for invalid supported inputs. Files remain unchanged.

Detection labels include common email, US phone, IPv4-shaped, SSN-shaped and
labeled credential patterns, including Authorization Bearer/Basic. These patterns
are incomplete and can misidentify data. This is output minimization, not a
general redaction tool: no sanitized copy of free text is produced, and original
files must still be protected. An empty `redactions` list is not a safety verdict.

See [Armando Gomez's contribution and reproduction notes](docs/CONTRIBUTION.md)
for regression examples, verification results and limitations.

## Verification

```powershell
python -m unittest discover
python -m ai_helpdesk_triage data\sample_tickets.json --pretty
```

## Responsible Use

This project uses sample tickets only. Do not commit real employee names, emails, phone numbers, IP addresses, secrets, medical data, law-enforcement data, or customer incidents.

