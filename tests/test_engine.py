import unittest

from ai_helpdesk_triage import Ticket, triage_ticket, triage_tickets


class TriageEngineTests(unittest.TestCase):
    def test_embedded_keywords_do_not_route_or_escalate(self):
        for text in ("download", "mushroom", "happy", "slowdown", "unblocked", "urgentlyish", "executively", "directorate", "breachedness"):
            with self.subTest(text=text):
                result = triage_ticket(Ticket("SYNTHETIC", text, ""))
                self.assertEqual((result.category, result.priority), ("general", "P4"))
                self.assertEqual(result.signals, ["needs_review"])

    def test_keywords_phrases_and_inflections_still_match(self):
        for text, category in (("WI-FI", "network"), ("sign-in", "identity"), ("sign   in", "identity"), ("access cards", "facilities"), ("printers", "endpoint"), ("applications", "software"), ("crashes", "endpoint"), ("viruses", "security")):
            with self.subTest(text=text):
                self.assertEqual(triage_ticket(Ticket("SYNTHETIC", text, "")).category, category)

    def test_security_indicators_override_other_keyword_counts(self):
        for indicator, priority in (("ransomware", "P1"), ("breaches", "P1"), ("compromised", "P1"), ("phishing", "P2"), ("malware", "P2")):
            with self.subTest(indicator=indicator):
                result = triage_ticket(Ticket("SYNTHETIC", indicator, "laptop desktop printer keyboard monitor slow crash windows"))
                self.assertEqual((result.category, result.priority, result.routing_group), ("security", priority, "Security Operations"))
                self.assertIn("security", result.signals)

    def test_real_impact_and_urgency_keywords_still_escalate(self):
        for text, priority, signal in (("service down", "P1", "service_impact"), ("outages", "P1", "service_impact"), ("cannot  work", "P2", "service_impact"), ("executive", "P2", "executive_request")):
            with self.subTest(text=text):
                result = triage_ticket(Ticket("SYNTHETIC", text, ""))
                self.assertEqual(result.priority, priority)
                self.assertIn(signal, result.signals)

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

