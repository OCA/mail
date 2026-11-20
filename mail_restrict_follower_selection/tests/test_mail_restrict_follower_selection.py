# Copyright (C) 2015 Therp BV <http://therp.nl>
# Copyright (C) 2017 Komit <http://www.komit-consulting.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests.common import (
    Command,
    HttpCase,
    TransactionCase,
    new_test_user,
    tagged,
)
from odoo.tools import mute_logger


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

    def test_message_subscribe_meet(self):
        self.partner.message_subscribe(partner_ids=self.partner.ids)
        self.assertIn(
            self.partner, self.partner.message_follower_ids.mapped("partner_id")
        )

    def test_message_subscribe_not_meet(self):
        """Programmatic subscriptions (not going through the wizard) must
        respect the domain too."""
        outsider = self.env["res.partner"].create(
            {"name": "Outsider", "email": "outsider@test.com"}
        )
        self.partner.message_subscribe(partner_ids=(self.partner | outsider).ids)
        followers = self.partner.message_follower_ids.mapped("partner_id")
        self.assertIn(self.partner, followers)
        self.assertNotIn(outsider, followers)

    def test_message_subscribe_current_user(self):
        """The current user is restricted like any other partner."""
        my_partner = self.env.user.partner_id
        self.assertNotIn(self.category_employees, my_partner.category_id)
        self.partner.message_subscribe(partner_ids=my_partner.ids)
        self.assertNotIn(
            my_partner, self.partner.message_follower_ids.mapped("partner_id")
        )

    def test_create_does_not_subscribe_creator_not_meet(self):
        user = new_test_user(
            self.env,
            login="restrict_follower_creator",
            groups="base.group_user,base.group_partner_manager",
        )
        record = self.env["res.partner"].with_user(user).create({"name": "New"})
        self.assertNotIn(
            user.partner_id, record.message_follower_ids.mapped("partner_id")
        )

    def test_create_subscribes_creator_meet(self):
        user = new_test_user(
            self.env,
            login="restrict_follower_creator",
            groups="base.group_user,base.group_partner_manager",
        )
        user.partner_id.category_id = self.category_employees
        record = self.env["res.partner"].with_user(user).create({"name": "New"})
        self.assertIn(user.partner_id, record.message_follower_ids.mapped("partner_id"))

    def test_message_subscribe_no_restrict_context(self):
        outsider = self.env["res.partner"].create(
            {"name": "Outsider", "email": "outsider@test.com"}
        )
        self.partner.with_context(no_restrict_follower=True).message_subscribe(
            partner_ids=outsider.ids
        )
        self.assertIn(outsider, self.partner.message_follower_ids.mapped("partner_id"))

    def test_message_subscribe_other_model_unrestricted(self):
        """Only the configured models are restricted."""
        outsider = self.env["res.partner"].create(
            {"name": "Outsider", "email": "outsider@test.com"}
        )
        record = self.env["mail.blacklist"].create({"email": "blocked@test.com"})
        record.message_subscribe(partner_ids=outsider.ids)
        self.assertIn(outsider, record.message_follower_ids.mapped("partner_id"))

    def test_auto_subscribe_assignee_not_meet(self):
        """Responsible users are subscribed through `_message_auto_subscribe`,
        bypassing `message_subscribe`: the domain must apply there too."""
        outsider_user = self.env["res.users"].create(
            {"name": "Outsider User", "login": "outsider_user"}
        )
        self.partner.write({"user_id": outsider_user.id})
        self.assertNotIn(
            outsider_user.partner_id,
            self.partner.message_follower_ids.mapped("partner_id"),
        )

    def test_auto_subscribe_assignee_meet(self):
        insider_user = self.env["res.users"].create(
            {"name": "Insider User", "login": "insider_user"}
        )
        insider_user.partner_id.category_id = self.category_employees
        self.partner.write({"user_id": insider_user.id})
        self.assertIn(
            insider_user.partner_id,
            self.partner.message_follower_ids.mapped("partner_id"),
        )

    def test_message_subscribe_existing_follower_subtypes(self):
        """Existing followers that do not meet the domain keep being
        editable (e.g. their subtypes), the module does not touch them."""
        outsider = self.env["res.partner"].create(
            {"name": "Outsider", "email": "outsider@test.com"}
        )
        self.partner.with_context(no_restrict_follower=True).message_subscribe(
            partner_ids=outsider.ids
        )
        subtype = self.env.ref("mail.mt_note")
        self.partner.message_subscribe(
            partner_ids=outsider.ids, subtype_ids=subtype.ids
        )
        follower = self.partner.message_follower_ids.filtered(
            lambda f: f.partner_id == outsider
        )
        self.assertEqual(follower.subtype_ids, subtype)

    def test_wizard_current_user(self):
        """Adding oneself via the wizard is restricted too."""
        # The superuser's partner (OdooBot) is archived and thus filtered out
        # of the wizard's many2many: use a regular user instead.
        user = new_test_user(
            self.env,
            login="restrict_follower_user",
            groups="base.group_user,base.group_partner_manager",
            email="restrict_follower_user@example.com",
        )
        my_partner = user.partner_id
        wizard = (
            self.env["mail.followers.edit"]
            .with_user(user)
            .create(
                {
                    "res_model": "res.partner",
                    "res_ids": str(self.partner.ids),
                    "operation": "add",
                    "partner_ids": [Command.link(my_partner.id)],
                }
            )
        )
        wizard.edit_followers()
        self.assertNotIn(
            my_partner, self.partner.message_follower_ids.mapped("partner_id")
        )


@tagged("post_install", "-at_install")
class TestMailRestrictFollowerSelectionHttp(HttpCase):
    def setUp(self):
        super().setUp()
        self.category_employees = self.env["res.partner.category"].create(
            {"name": "Employees"}
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "mail_restrict_follower_selection.domain.res.partner",
            "[('category_id.name', '=', 'Employees')]",
        )
        self.user = new_test_user(
            self.env,
            login="restrict_follower_http",
            groups="base.group_user,base.group_partner_manager",
        )
        self.record = self.env["res.partner"].create({"name": "Followed"})

    def _follow(self):
        self.authenticate(self.user.login, self.user.login)
        return self.make_jsonrpc_request(
            "/mail/thread/subscribe",
            {
                "res_model": "res.partner",
                "res_id": self.record.id,
                "partner_ids": self.user.partner_id.ids,
            },
        )

    def test_follow_button_not_meet(self):
        with self.assertRaises(Exception) as error, mute_logger("odoo.http"):
            self._follow()
        self.assertIn("UserError", str(error.exception))
        self.assertNotIn(
            self.user.partner_id, self.record.message_follower_ids.partner_id
        )

    def test_follow_button_meet(self):
        self.user.partner_id.category_id = self.category_employees
        self._follow()
        self.assertIn(self.user.partner_id, self.record.message_follower_ids.partner_id)
