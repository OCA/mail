"""Tests for mail_activity_restrict."""

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user


class TestMailActivityRestrict(TransactionCase):
    """Test access restrictions on mail.activity."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})
        cls.partner_model = cls.env["ir.model"]._get("res.partner")

        cls.activity_type_unrestricted = cls.env["mail.activity.type"].create(
            {
                "name": "Unrestricted Activity",
                "can_write_restrict": False,
            }
        )
        cls.activity_type_restricted = cls.env["mail.activity.type"].create(
            {
                "name": "Restricted Activity",
                "can_write_restrict": True,
            }
        )
        cls.user_assigned = new_test_user(
            cls.env,
            login="user_assigned@example.com",
            name="Assigned User",
            groups="base.group_user",
        )
        cls.user_other = new_test_user(
            cls.env,
            login="user_other@example.com",
            name="Other User",
            groups="base.group_user",
        )

    @classmethod
    def _create_activity(cls, activity_type, user):
        return cls.env["mail.activity"].create(
            {
                "activity_type_id": activity_type.id,
                "res_model_id": cls.partner_model.id,
                "res_id": cls.partner.id,
                "user_id": user.id,
                "summary": activity_type.name,
                "date_deadline": "2026-12-31",
            }
        )

    def test_unrestricted_activity_assigned_user_can_write(self):
        """Unrestricted activities keep the assignee's default write behavior."""
        activity = self._create_activity(
            self.activity_type_unrestricted, self.user_assigned
        )

        activity.with_user(self.user_assigned).write(
            {"summary": "Updated by Assigned User"}
        )

        self.assertEqual(activity.summary, "Updated by Assigned User")

    def test_restricted_activity_assigned_user_can_write(self):
        """Assigned users may still edit restricted activities."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned
        )

        activity.with_user(self.user_assigned).write(
            {"summary": "Updated by Assigned User"}
        )

        self.assertEqual(activity.summary, "Updated by Assigned User")

    def test_restricted_activity_other_user_cannot_write(self):
        """Non-assigned users cannot edit restricted activities."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned
        )

        with self.assertRaises(AccessError):
            activity.with_user(self.user_other).write(
                {"summary": "Updated by Other User"}
            )

    def test_restricted_activity_other_user_cannot_mark_done(self):
        """Restricted activities also block mark done for other users."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned
        )

        with self.assertRaises(AccessError):
            activity.with_user(self.user_other).action_done()

    def test_restricted_activity_assigned_user_can_mark_done(self):
        """Assigned users may mark restricted activities as done."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned
        )
        activity_id = activity.id

        activity.with_user(self.user_assigned).action_done()

        self.assertFalse(self.env["mail.activity"].browse(activity_id).exists())

    def test_restrict_field_default_value(self):
        """The restriction flag defaults to False."""
        activity_type = self.env["mail.activity.type"].create(
            {
                "name": "Default Activity Type",
            }
        )
        self.assertFalse(activity_type.can_write_restrict)

    def test_restrict_field_can_be_toggled(self):
        """The restriction flag can be toggled."""
        activity_type = self.env["mail.activity.type"].create(
            {
                "name": "Toggleable Activity Type",
                "can_write_restrict": False,
            }
        )
        self.assertFalse(activity_type.can_write_restrict)

        # Toggle on
        activity_type.write({"can_write_restrict": True})
        self.assertTrue(activity_type.can_write_restrict)

        # Toggle off
        activity_type.write({"can_write_restrict": False})
        self.assertFalse(activity_type.can_write_restrict)
