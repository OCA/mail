# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo.tests.common import TransactionCase


class TestFetchmailIncomingTestEml(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.domain = cls.env["mail.alias.domain"].search([], limit=1)

    def _wizard(self, raw):
        return self.env["fetchmail.incoming.test.eml"].create(
            {
                "eml_file": base64.b64encode(raw),
                "eml_filename": "message.eml",
            }
        )

    def _raw(self, email_to):
        return (
            b"From: Sender <sender@example.com>\r\n"
            b"To: " + email_to.encode() + b"\r\n"
            b"Subject: hello gateway\r\n"
            b"Message-Id: <replayed@example.com>\r\n"
            b"Content-Type: text/html; charset=UTF-8\r\n"
            b"\r\n"
            b"<p>body content</p>\r\n"
        )

    def test_build_raw_message_keeps_the_file_untouched(self):
        raw = self._raw(f"anything@{self.domain.name}")
        self.assertEqual(self._wizard(raw)._build_raw_message(), raw)

    def test_process_reaches_the_gateway(self):
        # No alias matches this address: the gateway must reject it. This proves
        # action_process really feeds message_process instead of swallowing the
        # email, without depending on any routable model.
        raw = self._raw(f"no-such-alias@{self.domain.name}")
        with self.assertRaisesRegex(ValueError, "No possible route found"):
            self._wizard(raw).action_process()
