import os
import unittest
from unittest.mock import patch

import prospecting_engine as engine


class OutreachCopyTests(unittest.TestCase):
    def test_indonesian_footer_uses_new_brand_and_links(self):
        body = engine.add_portfolio_offer("Halo tim bisnis,\n\nSaya melihat peluang untuk menyederhanakan alur kerja.", "id")
        self.assertIn("https://aigrowth.my.id", body)
        self.assertIn("@ai.growth.agency", body)
        self.assertIn("audit workflow", body.lower())
        self.assertIn("UNSUBSCRIBE", body)
        self.assertIn("Founder, AI Growth Agency", body)
        self.assertNotIn("agencyai.reybyoo.workers.dev", body)
        self.assertNotIn("Sonjaya Remote Business Services", body)
        self.assertIn("\nRey\nFounder, AI Growth Agency", body)
        self.assertNotIn("\\nRey", body)

    def test_english_footer_is_localized_and_has_new_brand(self):
        body = engine.add_portfolio_offer("Hi team,\n\nI noticed a possible way to simplify recurring work.", "en")
        self.assertIn("free", body.lower())
        self.assertIn("operating costs", body.lower())
        self.assertIn("https://aigrowth.my.id", body)
        self.assertIn("@ai.growth.agency", body)
        self.assertIn("reply UNSUBSCRIBE", body)
        self.assertIn("Founder, AI Growth Agency", body)
        self.assertNotIn("Jika email ini", body)
        self.assertNotIn("\\nRey", body)

    def test_language_defaults_to_indonesian_for_indonesian_query(self):
        lead = {"source_query": '"restaurant" "Jakarta" email', "recipient_email": "hello@example.com", "public_evidence": ""}
        self.assertEqual(engine.target_email_language(lead), "id")

    def test_language_defaults_to_english_for_international_query(self):
        lead = {"source_query": '"restaurant" "Singapore" "contact us" email', "recipient_email": "hello@example.com", "public_evidence": ""}
        self.assertEqual(engine.target_email_language(lead), "en")

    def test_search_queries_include_local_and_international_markets(self):
        with patch.dict(os.environ, {"QUERIES_PER_RUN": "6"}):
            queries = engine.search_queries()
        self.assertEqual(len(queries), 6)
        international = [q for q in queries if engine.is_international_query(q)]
        local = [q for q in queries if not engine.is_international_query(q)]
        self.assertGreaterEqual(len(international), 2)
        self.assertGreaterEqual(len(local), 2)


    def test_prospect_copy_removes_automation_vendor_names(self):
        body = engine.sanitize_prospect_copy("Kami membantu lewat otomasi menggunakan n8n.", "id")
        self.assertNotIn("n8n", body.lower())
        self.assertIn("otomasi", body.lower())

    def test_follow_up_is_first_due_after_three_days(self):
        from datetime import datetime, timedelta, timezone
        first = datetime(2026, 1, 1, tzinfo=timezone.utc)
        entry = {
            "status": "sent",
            "first_sent_at": first.isoformat().replace("+00:00", "Z"),
            "last_sent_at": first.isoformat().replace("+00:00", "Z"),
            "followup_count": 0,
        }
        self.assertFalse(engine._followup_due(entry, first + timedelta(days=2)))
        self.assertTrue(engine._followup_due(entry, first + timedelta(days=3)))

    def test_follow_ups_repeat_every_three_days(self):
        from datetime import datetime, timedelta, timezone
        first = datetime(2026, 1, 1, tzinfo=timezone.utc)
        entry = {
            "status": "sent",
            "first_sent_at": first.isoformat().replace("+00:00", "Z"),
            "last_sent_at": (first + timedelta(days=3)).isoformat().replace("+00:00", "Z"),
            "followup_count": 1,
        }
        self.assertFalse(engine._followup_due(entry, first + timedelta(days=5)))
        self.assertTrue(engine._followup_due(entry, first + timedelta(days=6)))

    def test_outbound_email_is_paused_without_imap_reply_tracking(self):
        with patch.object(engine, "ENABLE_AUTO_EMAIL", True), \
             patch.object(engine, "_smtp_configured", return_value=True), \
             patch.object(engine, "_imap_configured", return_value=False), \
             patch.object(engine, "_send_entry") as send_entry:
            state = {"send_day_wib": "", "sent_today": 0}
            self.assertFalse(engine._attempt_send({"record": {"id": "web-0123456789abcdef01234567"}}, state, "Subject", "Body"))
            send_entry.assert_not_called()

    def test_reply_status_and_preview_are_synced_to_dashboard(self):
        row = engine.dashboard_record({
            "record": {"id": "web-0123456789abcdef01234567", "status": "sent", "message_preview": "Initial email"},
            "status": "replied",
            "replied_at": "2026-01-04T12:00:00Z",
            "reply_preview": "Thanks, please send more details.",
            "error": None,
        })
        self.assertEqual(row["status"], "replied")
        self.assertEqual(row["replied_at"], "2026-01-04T12:00:00Z")
        self.assertEqual(row["message_preview"], "Thanks, please send more details.")

    def test_followup_templates_have_real_line_breaks_and_new_brand(self):
        entry = {"record": {"name": "Example Company"}, "email_language": "en"}
        body = engine._followup_copy(entry, 0)
        self.assertIn("\n\n", body)
        self.assertNotIn("\\n\\n", body)
        self.assertIn("https://aigrowth.my.id", body)
        self.assertIn("@ai.growth.agency", body)
        self.assertIn("Founder, AI Growth Agency", body)


if __name__ == "__main__":
    unittest.main()
