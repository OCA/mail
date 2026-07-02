# Copyright 2026 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from email.message import EmailMessage
from unittest import mock

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMailRecipientBlocklist(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.BlockRule = cls.env["mail.recipient.block.rule"]

    def test_default_amazon_rule_blocks_marketplace_aliases(self):
        self.assertTrue(
            self.BlockRule._is_blocked_email("abc123@marketplace.amazon.es")
        )
        self.assertTrue(
            self.BlockRule._is_blocked_email("abc123@marketplace.amazon.fr")
        )
        self.assertFalse(self.BlockRule._is_blocked_email("customer@example.com"))

    def test_regex_rule_validation(self):
        with self.assertRaises(ValidationError):
            self.BlockRule.create(
                {
                    "name": "Invalid regex",
                    "pattern_type": "regex",
                    "pattern": "[invalid",
                }
            )

    def test_configurable_domain_rule_blocks_other_recipients(self):
        self.BlockRule.create(
            {
                "name": "Example domain",
                "pattern_type": "domain",
                "pattern": "blocked.example.com",
            }
        )
        self.assertTrue(self.BlockRule._is_blocked_email("user@blocked.example.com"))
        self.assertFalse(self.BlockRule._is_blocked_email("user@example.com"))

    def test_inactive_rule_does_not_block_recipients(self):
        rule = self.BlockRule.create(
            {
                "name": "Inactive domain",
                "pattern_type": "domain",
                "pattern": "inactive.example.com",
                "active": False,
            }
        )
        self.assertFalse(rule.active)
        self.assertFalse(self.BlockRule._is_blocked_email("user@inactive.example.com"))

    def test_send_cancels_mail_addressed_only_to_blocked_recipient(self):
        mail = self.env["mail.mail"].create(
            {
                "email_to": "Customer <abc123@marketplace.amazon.es>",
                "subject": "Blocked",
                "body_html": "Blocked",
            }
        )
        with mock.patch(
            "odoo.addons.base.models.ir_mail_server.IrMailServer.connect"
        ) as connect_mock:
            mail.send()
        connect_mock.assert_not_called()
        self.assertEqual(mail.state, "cancel")
        self.assertIn("blocklist", mail.failure_reason)

    def test_prepare_outgoing_list_removes_blocked_recipient(self):
        mail = self.env["mail.mail"].create(
            {
                "email_to": (
                    "Customer <abc123@marketplace.amazon.es>, "
                    "Regular <regular@example.com>"
                ),
                "email_cc": "copy@marketplace.amazon.fr",
                "subject": "Partially blocked",
                "body_html": "Partially blocked",
            }
        )
        email_list = mail._prepare_outgoing_list()
        self.assertEqual(len(email_list), 1)
        self.assertEqual(email_list[0]["email_to"], ['"Regular" <regular@example.com>'])
        self.assertEqual(email_list[0]["email_cc"], [])
        self.assertEqual(email_list[0]["email_to_normalized"], ["regular@example.com"])

    def test_prepare_outgoing_list_removes_blocked_partner_recipient(self):
        amazon_partner = self.env["res.partner"].create(
            {"name": "Amazon", "email": "abc123@marketplace.amazon.it"}
        )
        regular_partner = self.env["res.partner"].create(
            {"name": "Regular", "email": "regular@example.com"}
        )
        mail = self.env["mail.mail"].create(
            {
                "recipient_ids": [(6, 0, (amazon_partner | regular_partner).ids)],
                "subject": "Partner recipients",
                "body_html": "Partner recipients",
            }
        )
        email_list = mail._prepare_outgoing_list()
        self.assertEqual(len(email_list), 1)
        self.assertEqual(email_list[0]["partner_id"], regular_partner)
        self.assertEqual(email_list[0]["email_to_normalized"], ["regular@example.com"])

    def test_send_email_cancels_direct_smtp_to_blocked_recipient(self):
        message = EmailMessage()
        message["Message-Id"] = "<test-amazon@example.com>"
        message["From"] = "sender@example.com"
        message["To"] = "Customer <abc123@marketplace.amazon.es>"
        with mock.patch(
            "odoo.addons.base.models.ir_mail_server.IrMailServer.connect"
        ) as connect_mock:
            result = self.env["ir.mail_server"].send_email(message)
        connect_mock.assert_not_called()
        self.assertEqual(result, "<test-amazon@example.com>")

    def test_filter_direct_smtp_message_removes_blocked_recipient(self):
        message = EmailMessage()
        message["Message-Id"] = "<test-mixed@example.com>"
        message["From"] = "sender@example.com"
        message["To"] = (
            "Customer <abc123@marketplace.amazon.es>, " "Regular <regular@example.com>"
        )
        message["Cc"] = "copy@marketplace.amazon.fr"
        has_remaining_recipients, blocked_recipients = self.env[
            "ir.mail_server"
        ]._filter_blocked_message_recipients(message)
        self.assertTrue(has_remaining_recipients)
        self.assertEqual(
            blocked_recipients,
            [
                '"Customer" <abc123@marketplace.amazon.es>',
                "copy@marketplace.amazon.fr",
            ],
        )
        self.assertEqual(message["To"], "Regular <regular@example.com>")
        self.assertFalse(message["Cc"])
