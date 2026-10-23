# Copyright 2026 Quartile (https://www.quartile.co)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import Command
from odoo.tests.common import TransactionCase


class TestMailAttachmentLinkMaxSize(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.mail_server"].search([]).active = False
        cls.mail_server = cls.env["ir.mail_server"].create(
            {
                "name": "Test Mail Server",
                "smtp_host": "smtp.example.com",
                "from_filter": "server.example.com",
            }
        )
        partner = cls.env["res.partner"].create({"name": "Test Partner"})
        cls.partner_attachment, cls.message_attachment = cls.env[
            "ir.attachment"
        ].create(
            [
                {
                    "name": "partner_attachment.txt",
                    "raw": b"x" * 200 * 1024,
                    "res_model": "res.partner",
                    "res_id": partner.id,
                },
                {
                    "name": "message_attachment.txt",
                    "raw": b"x" * 200 * 1024,
                    "res_model": "mail.message",
                },
            ]
        )

    def _convert(self, max_size, email_from="sender@example.com"):
        """Return a mail with both attachments, as it is about to be sent."""
        self.env["ir.config_parameter"].set_param(
            "base.default_max_email_size", max_size
        )
        mail = self.env["mail.mail"].create(
            {
                "attachment_ids": [
                    Command.set((self.partner_attachment | self.message_attachment).ids)
                ],
                "body_html": "<p>Test</p>",
                "email_from": email_from,
                "email_to": "recipient@example.com",
            }
        )
        list(mail._split_by_mail_configuration())
        return mail

    def test_max_size(self):
        self.assertEqual(self._convert(1).body_html, "<p>Test</p>")
        mail = self._convert(0.1)
        # Only the attachment of the partner is turned into a link
        self.assertIn(f"/web/content/{self.partner_attachment.id}?", mail.body_html)
        self.assertIn(self.partner_attachment.access_token, mail.body_html)
        self.assertNotIn(f"/web/content/{self.message_attachment.id}?", mail.body_html)
        # Sending again does not add the link twice
        body = mail.body_html
        mail._convert_attachments_to_links(0.1 * 1024 * 1024)
        self.assertEqual(mail.body_html, body)

    def test_mail_server_max_size(self):
        email_from = "sender@server.example.com"
        self.mail_server.max_email_size = 1
        self.assertEqual(self._convert(0.1, email_from).body_html, "<p>Test</p>")
        self.mail_server.max_email_size = 0.1
        self.assertNotEqual(self._convert(1, email_from).body_html, "<p>Test</p>")
