# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestSignatureMassEdit(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Signature Company"})
        cls.other_company = cls.env["res.company"].create(
            {"name": "Other Signature Company"}
        )
        cls.group_settings = cls.env.ref("base.group_system")
        cls.group_signature_mass_edit = cls.env.ref(
            "mail_user_signature_mass_edit.group_signature_mass_edit"
        )
        cls.user = new_test_user(
            cls.env,
            login="signature_user",
            groups="base.group_user",
            context={"no_reset_password": True},
            name="Signature User",
            company_id=cls.company.id,
            email="signature_user@example.com",
        )
        cls.other_user = new_test_user(
            cls.env,
            login="other_signature_user",
            groups="base.group_user",
            context={"no_reset_password": True},
            name="Other Signature User",
            company_id=cls.other_company.id,
            email="other_signature_user@example.com",
        )
        cls.portal_user = new_test_user(
            cls.env,
            login="portal_signature_user",
            groups="base.group_portal",
            context={"no_reset_password": True},
            name="Portal Signature User",
            company_id=cls.company.id,
            email="portal_signature_user@example.com",
        )

    def test_confirm_renders_signature_for_company_users(self):
        mass_edit = self.env["signature.mass.edit"].create(
            {
                "company_id": self.company.id,
                "signature": "<p>{{ object.name }} - {{ object.company_id.name }}</p>",
            }
        )
        self.assertEqual(
            mass_edit.display_name,
            "Signature Mass Edit - Signature Company",
        )
        self.assertEqual(mass_edit.user_count, 1)

        mass_edit.action_confirm()

        self.assertEqual(mass_edit.state, "done")
        self.assertEqual(mass_edit.processed_user_count, 1)
        self.assertEqual(
            self.user.signature,
            "<p>Signature User - Signature Company</p>",
        )
        self.assertNotEqual(
            self.other_user.signature,
            "<p>Other Signature User - Other Signature Company</p>",
        )

    def test_confirm_only_updates_internal_users(self):
        mass_edit = self.env["signature.mass.edit"].create(
            {
                "company_id": self.company.id,
                "signature": "<p>{{ object.name }}</p>",
            }
        )

        mass_edit.action_confirm()

        self.assertEqual(mass_edit.processed_user_count, 1)
        self.assertEqual(self.user.signature, "<p>Signature User</p>")
        self.assertNotEqual(self.portal_user.signature, "<p>Portal Signature User</p>")

    def test_confirm_only_updates_users_in_selected_groups(self):
        mass_edit = self.env["signature.mass.edit"].create(
            {
                "company_id": self.company.id,
                "group_ids": [(6, 0, self.group_settings.ids)],
                "signature": "<p>{{ object.name }}</p>",
            }
        )

        mass_edit.action_confirm()

        self.assertEqual(mass_edit.processed_user_count, 0)
        self.assertNotEqual(self.user.signature, "<p>Signature User</p>")

        action = mass_edit.action_reset_to_draft()
        self.assertTrue(action)
        self.assertEqual(mass_edit.state, "draft")

    def test_only_draft_records_can_be_confirmed(self):
        mass_edit = self.env["signature.mass.edit"].create(
            {
                "company_id": self.company.id,
                "signature": "<p>{{ object.name }}</p>",
            }
        )
        mass_edit.action_confirm()

        with self.assertRaisesRegex(UserError, "Only draft signature mass edits"):
            mass_edit.action_confirm()

    def test_action_view_users(self):
        mass_edit = self.env["signature.mass.edit"].create(
            {
                "company_id": self.company.id,
                "signature": "<p>{{ object.name }}</p>",
            }
        )

        action = mass_edit.action_view_users()

        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "res.users")
        self.assertEqual(action["view_mode"], "list,form")
        self.assertEqual(
            action["views"],
            [(False, "list"), (self.env.ref("base.view_users_form").id, "form")],
        )
        self.assertEqual(action["domain"], mass_edit._get_target_users_domain())

    def test_signature_mass_edit_group_can_confirm_without_user_admin_rights(self):
        marketing_user = new_test_user(
            self.env,
            login="signature_marketing_user",
            groups="mail_user_signature_mass_edit.group_signature_mass_edit",
            context={"no_reset_password": True},
            name="Signature Marketing User",
            company_id=self.company.id,
            company_ids=[(6, 0, self.company.ids)],
            email="signature_marketing_user@example.com",
        )
        mass_edit = (
            self.env["signature.mass.edit"]
            .with_user(marketing_user)
            .create(
                {
                    "company_id": self.company.id,
                    "group_ids": [(6, 0, self.group_signature_mass_edit.ids)],
                    "signature": "<p>{{ object.name }}</p>",
                }
            )
        )

        mass_edit.with_user(marketing_user).action_confirm()

        self.assertFalse(marketing_user.has_group("base.group_system"))
        self.assertEqual(mass_edit.state, "done")
        self.assertEqual(mass_edit.processed_user_count, 1)
        self.assertEqual(marketing_user.signature, "<p>Signature Marketing User</p>")
