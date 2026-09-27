from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import triage_tickets


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage IT helpdesk tickets from a JSON file.")
    parser.add_argument("input", type=Path, help="Path to a JSON array of tickets.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()

    try:
        # Bound the read itself, rather than trusting a size check before opening.
        with args.input.open("rb") as source:
            raw = source.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("Invalid ticket input.")
        tickets = json.loads(raw.decode("utf-8"))
        if not isinstance(tickets, list):
            raise ValueError("Invalid ticket input.")
        results = triage_tickets(tickets)
    except (OSError, ValueError, RecursionError):
        print('{"error": "Invalid ticket input."}', file=sys.stderr)
        return 2
    indent = 2 if args.pretty else None
    print(json.dumps(results, indent=indent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

