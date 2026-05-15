import unittest

from ai_helpdesk_triage import Ticket, triage_ticket, triage_tickets


class TriageEngineTests(unittest.TestCase):
    def test_security_incident_becomes_p1(self):
        ticket = Ticket(
            ticket_id="INC-1",
            subject="Possible ransomware",
            description="Multiple users report encrypted files and compromised workstation 10.0.0.8.",
            requester="analyst@example.com",
            affected_users=30,
        )

        result = triage_ticket(ticket)

        self.assertEqual(result.category, "security")
        self.assertEqual(result.priority, "P1")
        self.assertEqual(result.routing_group, "Security Operations")
        self.assertIn("security_incident", result.signals)
        self.assertIn("ip_address", result.redactions)

    def test_identity_ticket_routes_to_iam(self):
        result = triage_ticket(
            Ticket(
                ticket_id="INC-2",
                subject="Password reset",
                description="User is locked out after MFA change.",
            )
        )

        self.assertEqual(result.category, "identity")
        self.assertEqual(result.routing_group, "Identity and Access Management")
        self.assertEqual(result.priority, "P3")

    def test_json_contract_for_multiple_tickets(self):
        results = triage_tickets(
            [
                {"ticket_id": "A", "subject": "WiFi down", "description": "Network outage", "affected_users": 55},
                {"ticket_id": "B", "subject": "Install Teams", "description": "Need app installed"},
            ]
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["priority"], "P1")
        self.assertIn("suggested_response", results[1])


if __name__ == "__main__":
    unittest.main()

