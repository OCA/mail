# Copyright 2025 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.base.tests.common import BaseCommon


class TestMailSuggestedRecipientUnchecked(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test partner"})

    def test_partner_message_add_suggested_recipient(self):
        recipients = self.partner._message_get_suggested_recipients()
        self.assertFalse(recipients[0]["checked"])
