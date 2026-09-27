import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ai_helpdesk_triage import Ticket, triage_ticket, triage_tickets
from ai_helpdesk_triage.cli import main


class SensitiveOutputTests(unittest.TestCase):
    def test_sensitive_identity_never_echoed(self):
        for value in ("person@example.invalid", "password=SYNTHETIC_ONLY", "Jane Example", "555-123-4567", "192.0.2.1", "123-45-6789", "INC-password=SYNTHETIC_ONLY"):
            with self.subTest(value=value):
                result = triage_tickets([{"ticket_id": value, "subject": value, "description": value, "requester": value}])[0]
                self.assertNotIn(value, json.dumps(result))
                self.assertTrue(result["ticket_id"].startswith("anon-"))
                self.assertNotIn("subject", result)
                self.assertNotIn("requester", result)

    def test_identity_is_opaque_stable_and_distinct(self):
        first = triage_ticket(Ticket("INC-1", "", ""))
        self.assertTrue(first.ticket_id.startswith("anon-"))
        self.assertEqual(first.ticket_id, triage_ticket(Ticket("INC-1", "", "")).ticket_id)
        self.assertNotEqual(first.ticket_id, triage_ticket(Ticket("INC-2", "", "")).ticket_id)
        self.assertNotIn("INC-1", first.suggested_response)

    def test_detection_includes_identity_credentials_and_personal_patterns(self):
        for value, label in (("person@example.invalid", "email"), ("555-123-4567", "phone"), ("192.0.2.1", "ip_address"), ("123-45-6789", "ssn"), ('api_key: "synthetic only"', "possible_secret"), ("Authorization: Bearer synthetic-only", "possible_secret")):
            with self.subTest(value=value):
                self.assertIn(label, triage_ticket(Ticket(value, "", "")).redactions)


class InputValidationTests(unittest.TestCase):
    def test_invalid_records_rejected_without_values(self):
        for record in (None, [], "SYNTHETIC_SECRET", {"subject": []}, {"ticket_id": 123}, {"description": None}, {"requester": {}}, {"affected_users": True}, {"affected_users": -1}, {"affected_users": "bad-secret"}, {"affected_users": 1.5}, {"affected_users": 1000001}, {"subject": "x" * 10001}):
            with self.subTest(record_type=type(record).__name__):
                with self.assertRaisesRegex(ValueError, "^Invalid ticket input\\.$"):
                    triage_tickets([record])

    def test_direct_ticket_validation_and_batch_bounds(self):
        for ticket in (Ticket("INC-1", "x" * 10001, ""), Ticket("INC-1", "", "", affected_users=-1), Ticket("x" * 257, "", ""), Ticket("\ud800", "", "")):
            with self.assertRaises(ValueError):
                triage_ticket(ticket)
        for batch in ({}, "secret", [Ticket("INC-1", "", "")] * 1001):
            with self.assertRaises(ValueError):
                triage_tickets(batch)

    def test_valid_limits_and_zero_users(self):
        result = triage_tickets([{"ticket_id": "INC-1", "subject": "x" * 10000, "affected_users": 0}])
        self.assertEqual(result[0]["priority"], "P4")

    def test_cli_errors_do_not_echo_input_or_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "SYNTHETIC_SECRET.json"
            for content in ('{"SYNTHETIC_SECRET":', '[{"affected_users":"SYNTHETIC_SECRET"}]', '{}', '[NaN]', 'x' * 2000001):
                path.write_text(content, encoding="utf-8")
                stdout, stderr = io.StringIO(), io.StringIO()
                with patch("sys.argv", ["triage", str(path)]), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    self.assertEqual(main(), 2)
                self.assertEqual(stdout.getvalue(), "")
                self.assertEqual(stderr.getvalue(), '{"error": "Invalid ticket input."}\n')

    def test_cli_file_errors_and_invalid_utf8_are_generic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "SYNTHETIC_SECRET.json"
            for raw in (None, b"\xff"):
                if raw is not None:
                    path.write_bytes(raw)
                stdout, stderr = io.StringIO(), io.StringIO()
                with patch("sys.argv", ["triage", str(path)]), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    self.assertEqual(main(), 2)
                self.assertEqual(stdout.getvalue(), "")
                self.assertEqual(stderr.getvalue(), '{"error": "Invalid ticket input."}\n')
