# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class TestMailSuggestedRecipientUnchecked(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = (
            cls.env["res.partner"]
            .with_context(tracking_disable=True)
            .create({"name": "Suggested Recipient", "email": "suggested@example.com"})
        )

    def test_01_mail_suggested_recipient_unchecked_tour(self):
        self.start_tour(
            f"/odoo/res.partner/{self.partner.id}",
            "mail_suggested_recipient_unchecked.mail_suggested_recipient_unchecked_tour",
            login="admin",
        )
