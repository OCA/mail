# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestMailThread(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.demo_user = cls.env.ref("base.user_demo")

        cls.demo_user.write(
            {
                "country_id": cls.env.ref("base.be").id,
                "login": "demo",
                "notification_type": "inbox",
                "tz": "Europe/Brussels",
            }
        )
        cls.partner = cls.demo_user.partner_id

    def test_force_email_notification(self):
        """Test that notifications are sent by email when forced"""
        message = self.env["mail.message"].create(
            {
                "body": "Test message",
                "model": "res.partner",
                "res_id": self.partner.id,
            }
        )
        # Test without forcing email
        recipients = self.env["mail.thread"]._notify_get_recipients(
            message, {"partner_ids": [self.partner.id]}
        )

        for partner in recipients:
            self.assertEqual(
                partner["notif"],
                "inbox",
                "Should respect partner's notification preferences",
            )

        # Test with forcing email
        recipients = (
            self.env["mail.thread"]
            .with_context(force_notification_by_email=True)
            ._notify_get_recipients(message, {"partner_ids": [self.partner.id]})
        )
        for partner in recipients:
            self.assertEqual(
                partner["notif"],
                "email",
                "Should force email notification regardless of preferences",
            )
