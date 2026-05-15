# Codex Guide

## Purpose

This repository is a professional IT automation portfolio project. It should demonstrate helpdesk triage, explainable automation, JSON contracts, clean Python structure, and test coverage.

## Commands

```powershell
python -m ai_helpdesk_triage data\sample_tickets.json --pretty
python -m unittest discover
```

## Editing Rules

- Keep the classifier explainable. Every routing or priority decision should expose signals.
- Do not add real tickets or sensitive support data.
- Keep the engine dependency-light unless there is a clear reason.
- If adding an LLM provider later, keep deterministic tests and provide a no-key fallback.
- Update README examples when the output contract changes.

## Files

- `ai_helpdesk_triage/engine.py` - core classification logic.
- `ai_helpdesk_triage/cli.py` - command-line entry point.
- `data/sample_tickets.json` - synthetic sample tickets.
- `tests/test_engine.py` - behavior tests.

