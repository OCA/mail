# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestFetchmailIncomingTest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.domain = cls.env["mail.alias.domain"].search([], limit=1)

    def _wizard(self, **vals):
        return self.env["fetchmail.incoming.test"].create(
            {
                "email_from": "Sender <sender@example.com>",
                "email_to": f"anything@{self.domain.name}",
                "subject": "hello gateway",
                "body": "<p>body content</p>",
                **vals,
            }
        )

    def test_build_raw_message_carries_all_fields(self):
        raw = self._wizard(
            email_cc="cc@example.com", email_bcc="bcc@example.com"
        )._build_raw_message()
        text = raw.decode()
        self.assertIn("From: Sender <sender@example.com>", text)
        self.assertIn(f"To: anything@{self.domain.name}", text)
        self.assertIn("Cc: cc@example.com", text)
        self.assertIn("Bcc: bcc@example.com", text)
        self.assertIn("Subject: hello gateway", text)
        self.assertIn("body content", text)

    def test_process_reaches_the_gateway(self):
        # No alias matches this address: the gateway must reject it. This proves
        # action_process really feeds message_process instead of swallowing the
        # email, without depending on any routable model.
        with self.assertRaises(ValueError):
            self._wizard(email_to=f"no-such-alias@{self.domain.name}").action_process()
