# Copyright 2018 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo_test_helper import FakeModelLoader

from odoo import Command
from odoo.tests.common import TransactionCase


class TestMailActivityPartner(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.addClassCleanup(cls.loader.restore_registry)
        cls.loader.backup_registry()

        # Imported Test model must be done after the backup_registry
        # pylint: disable=import-outside-toplevel
        from .models import FakePartnerSubCustom, FakePartnerSubDefault

        cls.loader.update_registry((FakePartnerSubDefault, FakePartnerSubCustom))

        # disable tracking test suite wise
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.user_model = cls.env["res.users"].with_context(no_reset_password=True)

        cls.user_admin = cls.env.ref("base.user_root")

        cls.employee = cls.env["res.users"].create(
            {
                "company_id": cls.env.ref("base.main_company").id,
                "name": "Employee",
                "login": "csu",
                "email": "crmuser@yourcompany.com",
                "groups_id": [
                    Command.set(
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("base.group_partner_manager").id,
                        ],
                    )
                ],
            }
        )

        cls.partner_model = cls.env["ir.model"]._get("res.partner")

        activity_type_model = cls.env["mail.activity.type"]
        cls.activity1 = activity_type_model.create(
            {
                "name": "Initial Contact",
                "delay_count": 5,
                "delay_unit": "days",
                "summary": "ACT 1 : Presentation, barbecue, ... ",
                "res_model": cls.partner_model.model,
            }
        )
        cls.activity2 = activity_type_model.create(
            {
                "name": "Call for Demo",
                "delay_count": 6,
                "summary": "ACT 2 : I want to show you my ERP !",
                "res_model": cls.partner_model.model,
            }
        )

        cls.partner_01 = cls.env.ref("base.res_partner_1")

        cls.homer = cls.env["res.partner"].create(
            {
                "name": "Homer Simpson",
                "city": "Springfield",
                "street": "742 Evergreen Terrace",
                "street2": "Donut Lane",
            }
        )

        # test synchro of street3 on create
        cls.partner_10 = cls.env["res.partner"].create(
            {"name": "Bart Simpson", "parent_id": cls.homer.id, "type": "contact"}
        )

    def test_partner_for_activity(self):
        self.act1 = (
            self.env["mail.activity"]
            .sudo()
            .create(
                {
                    "activity_type_id": self.activity1.id,
                    "note": "Partner activity 1.",
                    "res_id": self.partner_01.id,
                    "res_model_id": self.partner_model.id,
                    "user_id": self.user_admin.id,
                }
            )
        )

        self.act2 = (
            self.env["mail.activity"]
            .with_user(self.employee)
            .create(
                {
                    "activity_type_id": self.activity2.id,
                    "note": "Partner activity 10.",
                    "res_id": self.partner_10.id,
                    "res_model_id": self.partner_model.id,
                    "user_id": self.employee.id,
                }
            )
        )

        # Check partner_id of created activities
        self.assertEqual(self.act1.partner_id, self.partner_01)
        self.assertEqual(self.act2.partner_id, self.partner_10)

        # Check commercial_partner_id for created activities
        self.assertEqual(self.act1.commercial_partner_id, self.partner_01)
        self.assertEqual(self.act2.commercial_partner_id, self.homer)

    def test_default_partner_field_name(self):
        """Test that _get_partner_field_name returns 'partner_id' by default."""
        fake_model = self.env["fakepartner.subdefault"]
        self.assertEqual(fake_model._get_partner_field_name(), "partner_id")

    def test_custom_partner_field_name(self):
        """Test that _get_partner_field_name can be overridden."""
        fake_model = self.env["fakepartner.subcustom"]
        self.assertEqual(fake_model._get_partner_field_name(), "contact_id")

    def test_activity_partner_need_update_default(self):
        """Test _activity_partner_need_update with default partner_id field."""
        fake_model = self.env["fakepartner.subdefault"]
        self.assertTrue(fake_model._activity_partner_need_update({"partner_id": 1}))
        self.assertFalse(fake_model._activity_partner_need_update({"name": "test"}))

    def test_activity_partner_need_update_custom(self):
        """Test _activity_partner_need_update detects the custom partner field."""
        fake_model = self.env["fakepartner.subcustom"]
        self.assertTrue(fake_model._activity_partner_need_update({"contact_id": 1}))
        self.assertFalse(fake_model._activity_partner_need_update({"name": "test"}))
        # the default partner_id field should NOT trigger update on this model
        self.assertFalse(fake_model._activity_partner_need_update({"partner_id": 1}))

    def test_activity_partner_synced_on_create_custom(self):
        """Test that creating a record syncs activity partner via custom field."""
        fake_model = self.env["fakepartner.subcustom"]
        ir_model = self.env["ir.model"]._get("fakepartner.subcustom")
        activity_type = self.env["mail.activity.type"].create(
            {
                "name": "Test Activity",
                "res_model": ir_model.model,
            }
        )
        rec = fake_model.create({"name": "Test Record", "contact_id": self.homer.id})
        activity = self.env["mail.activity"].create(
            {
                "activity_type_id": activity_type.id,
                "res_id": rec.id,
                "res_model_id": ir_model.id,
                "user_id": self.user_admin.id,
            }
        )
        self.assertEqual(activity.partner_id, self.homer)

    def test_activity_partner_synced_on_write_custom(self):
        """Test that updating the custom partner field syncs activity partner."""
        fake_model = self.env["fakepartner.subcustom"]
        ir_model = self.env["ir.model"]._get("fakepartner.subcustom")
        activity_type = self.env["mail.activity.type"].create(
            {
                "name": "Test Activity",
                "res_model": ir_model.model,
            }
        )
        rec = fake_model.create({"name": "Test Record", "contact_id": self.homer.id})
        activity = self.env["mail.activity"].create(
            {
                "activity_type_id": activity_type.id,
                "res_id": rec.id,
                "res_model_id": ir_model.id,
                "user_id": self.user_admin.id,
            }
        )
        self.assertEqual(activity.partner_id, self.homer)
        # update the custom partner field to another partner
        rec.write({"contact_id": self.partner_01.id})
        self.assertEqual(activity.partner_id, self.partner_01)
