# Copyright 2025 Onestein - Anjeel Haria
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.base.tests.common import BaseCommon


class TestMailPartnerOptOut(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            [{"name": "Mr. Odoo", "email": "mrodoo@xyz.com"}]
        )

    def test_mail_blacklist_add(self):
        self.partner.mail_blacklist_add()
        self.assertTrue(
            self.env["mail.blacklist"].search(
                [("email", "=", "mrodoo@xyz.com")], limit=1
            )
        )
