# Copyright (C) 2015 Therp BV <http://therp.nl>
# Copyright (C) 2017 Komit <http://www.komit-consulting.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests.common import Command, TransactionCase


class TestMailRestrictFollowerSelection(TransactionCase):
    def setUp(self):
        super().setUp()
        self.category_employees = self.env["res.partner.category"].create(
            {"name": "Employees"}
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "mail_restrict_follower_selection.domain.res.partner",
            "[('category_id.name', '=', 'Employees')]",
        )

        self.partner = self.env["res.partner"].create(
            {
                "name": "Partner",
                "category_id": self.category_employees,
                "email": "test@test.com",
            }
        )
        self.switzerland = self.env.ref("base.ch")

    def _use_ref_in_domain(self):
        """Change the general domain to test the safe_eval."""
        country_id = self.env.ref("base.ch").id
        self.env["ir.config_parameter"].sudo().set_param(
            "mail_restrict_follower_selection.domain",
            f"[('country_id', '!=', {country_id})]",
        )

    def test_fields_view_get(self):
        result = self.env["mail.followers.edit"].get_view(view_type="form")
        for field in etree.fromstring(result["arch"]).xpath(
            '//field[@name="partner_ids"]'
        ):
            self.assertTrue(field.get("domain"))

    def _send_action(self):
        wizard = self.env["mail.followers.edit"].create(
            {
                "res_model": "res.partner",
                "res_ids": str(self.partner.ids),
                "operation": "add",
                "partner_ids": [Command.link(self.partner.id)],
            }
        )
        wizard.edit_followers()

    def test_followers_meet(self):
        self._send_action()
        self.assertIn(
            self.partner, self.partner.message_follower_ids.mapped("partner_id")
        )

    def test_followers_not_meet(self):
        self.partner.write({"category_id": False})
        self._send_action()
        self.assertNotIn(
            self.partner, self.partner.message_follower_ids.mapped("partner_id")
        )

    def test_get_view_eval(self):
        """Check using safe_eval in field_view_get."""
        self._use_ref_in_domain()
        result = self.env["mail.followers.edit"].get_view(view_type="form")
        for field in etree.fromstring(result["arch"]).xpath(
            '//field[@name="partner_ids"]'
        ):
            domain = field.get("domain")
            self.assertTrue(domain.find("country_id") > 0)
            self.assertTrue(domain.find(str(self.switzerland.id)) > 0)

    def test_get_view_uses_view_ref_context_key(self):
        """The per-model domain must be applied when the model is forwarded
        through `restrict_follower_res_model_view_ref` (the only key shape
        that survives the web client's loadViews context filtering)."""
        result = (
            self.env["mail.followers.edit"]
            .with_context(restrict_follower_res_model_view_ref="res.partner")
            .get_view(view_type="form")
        )
        for field in etree.fromstring(result["arch"]).xpath(
            '//field[@name="partner_ids"]'
        ):
            domain = field.get("domain")
            self.assertIn("category_id.name", domain)
