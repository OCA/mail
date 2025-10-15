# Copyright 2017 ForgeFlow S.L.
#   (http://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.addons.base.tests.common import BaseCommon


class TestBaseSearchMailContent(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel_obj = cls.env["discuss.channel"]

    def test_base_search_mail_content_1(self):
        res = self.channel_obj.search([("message_content", "%", "xxxyyyzzz")])
        self.assertFalse(res, "You have a channel with xxxyyyzzz :O")

    def test_base_search_mail_content_2(self):
        res = self.channel_obj.get_view(
            False, "search", load_fields=False, load_filters=True, toolbar=True
        )
        self.assertIn(
            "message_content",
            res["models"][self.channel_obj._name],
            "message_content field was not detected",
        )

    def test_base_search_mail_content_3(self):
        Partner = self.env["res.partner"]
        partner = Partner.create({"name": "Test Partner"})
        partner.message_post(
            subject="Hello World",
        )
        partner.message_post(
            subject="Lorem ipsum",
        )
        # If positive, the partner should be in the result
        partner_find = Partner.search([("message_content", "ilike", "Hello World")])
        self.assertIn(partner, partner_find)
        # If negative, the partner should be not in the result
        partner_find = Partner.search([("message_content", "not ilike", "Hello World")])
        self.assertNotIn(partner, partner_find)
