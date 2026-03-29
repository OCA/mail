# Copyright 2026 Reinaldo J. Menendez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestMailActivityReassignOnArchive(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, lang="en_US")
        )

        cls.user_to_archive = cls.env["res.users"].create(
            {
                "name": "User To Archive",
                "login": "user_to_archive",
                "email": "user_to_archive@example.com",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.reassign_user = cls.env["res.users"].create(
            {
                "name": "Reassign User",
                "login": "reassign_user",
                "email": "reassign_user@example.com",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.test_partner = cls.env["res.partner"].create({"name": "Test Partner"})
        cls.activity_type = cls.env.ref("mail.mail_activity_data_todo")

    def _create_activity(self, user):
        return self.test_partner.activity_schedule(
            activity_type_id=self.activity_type.id,
            user_id=user.id,
            summary=f"Activity for {user.name}",
        )

    def _enable_feature(self, reassign_user=None, restore=False):
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("mail_activity_reassign_on_archive.enabled", "True")
        icp.set_param(
            "mail_activity_reassign_on_archive.restore_on_unarchive",
            "True" if restore else "False",
        )
        if reassign_user:
            icp.set_param(
                "mail_activity_reassign_on_archive.reassign_user_id", reassign_user.id
            )

    def _disable_feature(self):
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("mail_activity_reassign_on_archive.enabled", "False")

    def test_feature_disabled_standard_behavior(self):
        """When feature is disabled, activities should be deleted."""
        self._disable_feature()
        activity = self._create_activity(self.user_to_archive)
        self.user_to_archive.action_archive()
        self.assertFalse(activity.exists())

    def test_feature_enabled_reassign_activities(self):
        """When feature is enabled, activities should be reassigned."""
        self._enable_feature(self.reassign_user)
        activity = self._create_activity(self.user_to_archive)
        self.user_to_archive.action_archive()
        self.assertTrue(activity.exists())
        self.assertEqual(activity.user_id, self.reassign_user)
        self.assertEqual(activity.original_user_id, self.user_to_archive)

    def test_unarchive_restores_activities(self):
        """Unarchiving user restores activities when enabled."""
        self._enable_feature(self.reassign_user, restore=True)
        activity = self._create_activity(self.user_to_archive)
        self.user_to_archive.action_archive()
        self.assertEqual(activity.user_id, self.reassign_user)
        self.user_to_archive.action_unarchive()
        self.assertEqual(activity.user_id, self.user_to_archive)
        self.assertFalse(activity.original_user_id)

    def test_unarchive_no_restore_when_disabled(self):
        """Unarchiving user keeps activities when restore is disabled."""
        self._enable_feature(self.reassign_user, restore=False)
        activity = self._create_activity(self.user_to_archive)
        self.user_to_archive.action_archive()
        self.user_to_archive.action_unarchive()
        self.assertEqual(activity.user_id, self.reassign_user)

    def test_reassign_user_inactive_raises_error(self):
        """Archiving with inactive reassign user raises ValidationError."""
        self._enable_feature(self.reassign_user)
        self._create_activity(self.user_to_archive)
        # Directly deactivate without triggering the reassign logic
        self.reassign_user.write({"active": False})
        with self.assertRaises(ValidationError) as error:
            self.user_to_archive.action_archive()
        self.assertIn(
            "The user designated for activity reassignment must be active.",
            str(error.exception),
        )

    def test_activity_reassign_to_user(self):
        """Test mail.activity.reassign_to_user method."""
        activity = self._create_activity(self.user_to_archive)
        self.assertEqual(activity.user_id, self.user_to_archive)
        self.assertFalse(activity.original_user_id)

        activity.reassign_to_user(self.reassign_user)

        self.assertEqual(activity.user_id, self.reassign_user)
        self.assertEqual(activity.original_user_id, self.user_to_archive)

    def test_activity_restore_to_original_user(self):
        """Test mail.activity.restore_to_original_user method."""
        activity = self._create_activity(self.user_to_archive)
        activity.reassign_to_user(self.reassign_user)
        self.assertEqual(activity.user_id, self.reassign_user)

        activity.restore_to_original_user()

        self.assertEqual(activity.user_id, self.user_to_archive)
        self.assertFalse(activity.original_user_id)

    def test_restore_skips_inactive_original_user(self):
        """Restore skips activities whose original user is inactive."""
        self._enable_feature(self.reassign_user, restore=True)
        activity = self._create_activity(self.user_to_archive)
        self.user_to_archive.action_archive()
        self.assertEqual(activity.user_id, self.reassign_user)

        # original_user_id is archived, restore should not change user_id
        activity.restore_to_original_user()
        self.assertEqual(activity.user_id, self.reassign_user)

    def test_feature_enabled_no_reassign_user_raises_error(self):
        """When enabled but no reassign user configured, raise ValidationError."""
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("mail_activity_reassign_on_archive.enabled", "True")
        icp.set_param("mail_activity_reassign_on_archive.reassign_user_id", "False")
        self._create_activity(self.user_to_archive)
        with self.assertRaises(ValidationError) as error:
            self.user_to_archive.action_archive()
        self.assertIn(
            "Activity reassignment is enabled but no reassign user is configured",
            str(error.exception),
        )

    def test_archiving_reassign_user_raises_error(self):
        """Archiving the designated reassign user raises ValidationError."""
        self._enable_feature(self.reassign_user)
        self._create_activity(self.user_to_archive)
        with self.assertRaises(ValidationError) as error:
            self.reassign_user.action_archive()
        self.assertIn(
            "You cannot archive a user designated for activity reassignment.",
            str(error.exception),
        )

    def test_archive_multiple_users_reassigns_all_activities(self):
        """Archiving multiple users reassigns all their activities."""
        second_user = self.env["res.users"].create(
            {
                "name": "Second User",
                "login": "second_user",
                "email": "second_user@example.com",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self._enable_feature(self.reassign_user)
        activity1 = self._create_activity(self.user_to_archive)
        activity2 = self._create_activity(second_user)

        (self.user_to_archive | second_user).action_archive()

        self.assertTrue(activity1.exists())
        self.assertTrue(activity2.exists())
        self.assertEqual(activity1.user_id, self.reassign_user)
        self.assertEqual(activity2.user_id, self.reassign_user)
        self.assertEqual(activity1.original_user_id, self.user_to_archive)
        self.assertEqual(activity2.original_user_id, second_user)

    def test_unarchive_multiple_users_restores_all_activities(self):
        """Unarchiving multiple users restores all their activities."""
        second_user = self.env["res.users"].create(
            {
                "name": "Second User",
                "login": "second_user",
                "email": "second_user@example.com",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self._enable_feature(self.reassign_user, restore=True)
        activity1 = self._create_activity(self.user_to_archive)
        activity2 = self._create_activity(second_user)

        # Archive both users
        (self.user_to_archive | second_user).action_archive()
        self.assertEqual(activity1.user_id, self.reassign_user)
        self.assertEqual(activity2.user_id, self.reassign_user)

        # Unarchive both users
        (self.user_to_archive | second_user).action_unarchive()

        self.assertEqual(activity1.user_id, self.user_to_archive)
        self.assertEqual(activity2.user_id, second_user)
        self.assertFalse(activity1.original_user_id)
        self.assertFalse(activity2.original_user_id)
