# Reliable helpdesk keyword matching

Author: Armando Gomez
Date: 2026-09-26
Branch: `contribution/techops-reliability`

## Problem and root cause

Category scoring, signal detection and priority each used substring membership.
`download` therefore matched `down` and received P1 plus `service_impact`;
`mushroom` routed to Facilities Support through `room`; `happy` matched `app`.
Separately, the largest category keyword count won routing. An endpoint-heavy
description could defeat `ransomware`, and the priority rule required a security
category before assigning the incident P1.

## Change

A shared matcher requires word boundaries around complete keywords and phrases.
It supports case-insensitive matches, whitespace between phrase words, existing
`wi-fi` / `sign-in` spellings and an explicit table of common plural forms.
There is no broad stemming: `down` cannot match `download` and `blocked` cannot
match `unblocked`. Each canonical keyword still contributes at most one hit.

Any matched security category keyword now routes to Security Operations,
regardless of other category counts. Ransomware, breach/breaches and compromised
receive P1; other security keywords receive at least P2. Existing impact rules
can still escalate them to P1. Non-security score ties retain category declaration
order. The matching change retained JSON fields and SLA targets. The September 27
output hardening below changes the meaning of `ticket_id`.

## Reproduce and verify

From the repository root, using the available local Python environment:

```powershell
& D:\TechOpsagent\.venv\Scripts\python.exe -m unittest discover
& D:\TechOpsagent\.venv\Scripts\python.exe -m ai_helpdesk_triage data\matching_regressions.json --pretty
& D:\TechOpsagent\.venv\Scripts\python.exe -m ai_helpdesk_triage data\sample_tickets.json --pretty
```

All fixtures are synthetic; no credentials, model runtime or network is needed.
With an ordinary Python installation, replace the interpreter path with `python`.

| Synthetic input | Before | After |
| --- | --- | --- |
| `download` | general / P1 / service_impact | general / P4 / needs_review |
| `mushroom` | facilities / P4 | general / P4 |
| `happy` | software / P4 | general / P4 |
| ransomware + laptop desktop printer keyboard monitor slow crash windows | endpoint / P4 / Desktop Support | security / P1 / Security Operations |
| WI-FI down + Network outage | network / P1 | network / P1 |

Verification recorded on 2026-09-26:

- Unmodified baseline: `Ran 3 tests` / `OK`.
- New regressions against old implementation: `Ran 7 tests` / `FAILED (failures=16)`.
- After implementation: `Ran 7 tests` / `OK`.

The four new test methods include table-driven subtests covering false matches,
plural and phrase preservation, mixed-category security precedence, and real
impact/urgency matches. Subtests are cases within methods, not separate test counts.

The existing `.github/workflows/ci.yml` runs unittest discovery and the sample
CLI on Ubuntu with Python 3.10, 3.11 and 3.12 for pushes and pull requests targeting
`main`. It will include these regressions when the contribution is submitted.
No duplicate workflow was added, and no remote CI run is claimed here.

## Operational value and limits

This reduces avoidable P1 pages and misrouted queues while retaining explicit
security escalation. It demonstrates Python debugging, regression-first testing,
regular expressions, deterministic policy design, JSON CLI validation and
technical handoff writing relevant to TechOps support automation.

This remains an English keyword heuristic, not semantic understanding. Negation,
quoted examples and historical incidents are not understood: `no ransomware`
still escalates. Security precedence deliberately favors review and can create
false positives. Hyphens act as boundaries; plurals are supported only by the
explicit table, and arbitrary verb forms are not inferred. Subject and description
are combined, so phrases can span that boundary. Human review remains necessary.

`confidence` is an uncalibrated heuristic score, not a probability or measured
accuracy. The legacy `redactions` field reports detected data types; it does not
sanitize input or remove sensitive values. Detection is incomplete and the input
file remains unchanged. No production integration or real ticket processing was
performed. Implementation evidence was collected before publication; the contribution branch carries the reviewable patch.

## 2026-09-27: minimize sensitive output and validate input

Author: Armando Gomez.

The original detector only returned labels, while `ticket_id` was copied into
both the result and suggested response. A caller could accidentally place an
email, personal name or credential in that field and expose it downstream.
The correction omits raw IDs from response text and replaces returned IDs with
HMAC-SHA256 references using a randomly generated process-local key. Equal IDs
produce equal references within a process; references change after restart.
There is no plain deterministic hash that can be guessed offline without the key.
Raw subject, description and requester values remain excluded entirely.

This deliberately avoids adding free-text output with uncertain redaction.
`redactions` remains a legacy detection-label field, with ID inspection and
SSN-shaped/Authorization credential patterns added. It is best effort, not
proof that a ticket is sanitized. Pseudonymous references and classification
labels are still contextual information; original files and process memory need
normal access controls. No disk ID map or key is created. References are not
authentication tokens and are not stable cross-process integration IDs.

Compatibility: consumers must correlate batch results by their input order.
Types and field names remain unchanged, but raw ID joins must be updated.
The suggested response no longer includes any ticket reference. See README's
input/output contract for exact size and type limits. Invalid supported input
raises generic ValueError; CLI validation/file errors return exit 2 and
`{"error": "Invalid ticket input."}` on stderr with empty stdout.

Verification with `D:\TechOpsagent\.venv\Scripts\python.exe -m unittest discover`:

- Security baseline: `Ran 7 tests` / `OK`.
- Initial new regressions before implementation: `Ran 14 tests` / `FAILED (failures=25, errors=4)`.
- Final suite including missing-file and UTF-8 coverage: `Ran 15 tests` / `OK`.
- Synthetic matching CLI exits 0, preserving general/P4, security/P1 and network/P1 decisions with opaque references.
- `git diff --check` exits 0 (Windows line-ending warnings only).

All regression values are synthetic. No live tickets, network calls, model
downloads, runtime startup or new dependencies are required. This update adds
input validation, data minimization and error-contract testing to the original
TechOps contribution. No remote CI result is asserted for these local changes.
