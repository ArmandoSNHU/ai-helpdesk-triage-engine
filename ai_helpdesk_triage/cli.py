from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import triage_tickets


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage IT helpdesk tickets from a JSON file.")
    parser.add_argument("input", type=Path, help="Path to a JSON array of tickets.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()

    tickets = json.loads(args.input.read_text(encoding="utf-8"))
    results = triage_tickets(tickets)
    indent = 2 if args.pretty else None
    print(json.dumps(results, indent=indent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

