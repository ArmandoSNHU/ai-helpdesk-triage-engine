# AI Helpdesk Triage Engine

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Use Case](https://img.shields.io/badge/Use%20Case-IT%20Helpdesk%20Automation-2563eb)](#what-it-does)
[![Tests](https://img.shields.io/badge/Tests-unittest-success)](#verification)

AI Helpdesk Triage Engine is a portfolio-ready ticket classification system for IT support queues. It turns raw helpdesk tickets into structured routing decisions with priority, confidence, SLA target, detected signals, data-redaction notes, and a suggested analyst response.

The current engine is deterministic and explainable by design, which makes it easy to test and safe to run without an API key. It is structured so an LLM classifier can be added later behind the same output contract.

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

```json
{
  "ticket_id": "INC-1002",
  "category": "security",
  "priority": "P1",
  "routing_group": "Security Operations",
  "sla_minutes": 15,
  "confidence": 0.94,
  "signals": ["ransomware", "multiple_users", "security"],
  "redactions": ["email", "ip_address"],
  "suggested_response": "We have classified this as a P1 security incident..."
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

The output is explainable: each decision includes the signals that drove routing and priority. This is important for IT operations because analysts need to trust and override automation.

## Verification

```powershell
python -m unittest discover
python -m ai_helpdesk_triage data\sample_tickets.json --pretty
```

## Responsible Use

This project uses sample tickets only. Do not commit real employee names, emails, phone numbers, IP addresses, secrets, medical data, law-enforcement data, or customer incidents.

