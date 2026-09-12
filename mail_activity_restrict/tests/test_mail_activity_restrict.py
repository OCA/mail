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
        # Write access on res.partner makes core mail grant write on the
        # activities of that partner, so this user is only ever stopped by
        # this module. Without it a test cannot tell the two apart.
        cls.user_manager = new_test_user(
            cls.env,
            login="user_manager@example.com",
            name="Document Manager",
            groups="base.group_user,base.group_partner_manager",
        )
        cls.user_other = new_test_user(
            cls.env,
            login="user_other@example.com",
            name="Other User",
            groups="base.group_user",
        )

    @classmethod
    def _create_activity(cls, activity_type, user, env=None):
        return (env or cls.env)["mail.activity"].create(
            {
                "activity_type_id": activity_type.id,
                "res_model_id": cls.partner_model.id,
                "res_id": cls.partner.id,
                "user_id": user.id if user else False,
                "summary": activity_type.name,
                "date_deadline": "2026-12-31",
            }
        )

    # ------------------------------------------------------------------
    # create: assigning somebody else must stay possible
    # ------------------------------------------------------------------

    def test_create_restricted_for_another_user(self):
        """Creating a restricted activity for somebody else is allowed."""
        activity = self._create_activity(
            self.activity_type_restricted,
            self.user_assigned,
            env=self.env(user=self.user_manager),
        )

        self.assertEqual(activity.user_id, self.user_assigned)

    def test_create_restricted_for_another_user_from_code(self):
        """activity_schedule() for somebody else is allowed.

        Restricted activity types are meant to be used as an approval step
        created from code, which assigns the approver rather than the caller.
        """
        activity = self.partner.with_user(self.user_manager).activity_schedule(
            activity_type_id=self.activity_type_restricted.id,
            user_id=self.user_assigned.id,
            summary="Approval",
        )

        self.assertEqual(activity.user_id, self.user_assigned)

    # ------------------------------------------------------------------
    # write / done: only the assigned user
    # ------------------------------------------------------------------

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

    def test_restricted_activity_document_manager_cannot_write(self):
        """Write access on the related document does not lift the restriction."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned
        )

        with self.assertRaises(AccessError):
            activity.with_user(self.user_manager).write({"summary": "Nope"})

    def test_unrestricted_activity_document_manager_can_write(self):
        """Counter test: core grants that same user write without the flag."""
        activity = self._create_activity(
            self.activity_type_unrestricted, self.user_assigned
        )

        activity.with_user(self.user_manager).write({"summary": "Updated"})

        self.assertEqual(activity.summary, "Updated")

    def test_restricted_activity_creator_cannot_write(self):
        """Having created the activity does not grant write on it."""
        activity = self._create_activity(
            self.activity_type_restricted,
            self.user_assigned,
            env=self.env(user=self.user_manager),
        )

        with self.assertRaises(AccessError):
            activity.with_user(self.user_manager).write({"summary": "Nope"})

    def test_restricted_activity_other_user_cannot_write(self):
        """Non-assigned users cannot edit restricted activities."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned
        )

        with self.assertRaises(AccessError):
            activity.with_user(self.user_other).write(
                {"summary": "Updated by Other User"}
            )

    def test_restricted_activity_assigned_user_can_mark_done(self):
        """Assigned users may mark restricted activities as done."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned
        )

        activity.with_user(self.user_assigned).action_done()

        self.assertEqual(activity.state, "done")

    def test_restricted_activity_document_manager_cannot_mark_done(self):
        """Restricted activities also block mark done for other users."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned
        )

        with self.assertRaises(AccessError):
            activity.with_user(self.user_manager).action_done()

    # ------------------------------------------------------------------
    # unlink
    # ------------------------------------------------------------------

    def test_restricted_activity_assigned_user_can_unlink(self):
        """The assigned user may delete a restricted activity."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned
        )

        activity.with_user(self.user_assigned).unlink()

        self.assertFalse(activity.exists())

    def test_restricted_activity_document_manager_cannot_unlink(self):
        """The restriction covers unlink, not only write."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned
        )

        with self.assertRaises(AccessError):
            activity.with_user(self.user_manager).unlink()

    # ------------------------------------------------------------------
    # reassignment: only the assigned user hands the activity over
    # ------------------------------------------------------------------

    def test_restricted_activity_assigned_user_can_reassign(self):
        """The assigned user may hand a restricted activity over.

        The assignee here is the user with document write access, because
        core subscribes the new assignee to the document on reassignment.
        """
        activity = self._create_activity(
            self.activity_type_restricted, self.user_manager
        )

        activity.with_user(self.user_manager).write({"user_id": self.user_assigned.id})

        self.assertEqual(activity.user_id, self.user_assigned)

    def test_restricted_activity_creator_cannot_reassign(self):
        """The creator cannot take a restricted activity away from its assignee."""
        activity = self._create_activity(
            self.activity_type_restricted,
            self.user_assigned,
            env=self.env(user=self.user_manager),
        )

        with self.assertRaises(AccessError):
            activity.with_user(self.user_manager).write(
                {"user_id": self.user_manager.id}
            )

    def test_restricted_activity_reassignment_is_final(self):
        """After handing it over, the previous assignee is out.

        This follows from the rule itself: only the assigned user may act on
        the activity, so giving it away cannot be undone by the giver.
        """
        activity = self._create_activity(
            self.activity_type_restricted, self.user_manager
        )
        activity.with_user(self.user_manager).write({"user_id": self.user_assigned.id})

        with self.assertRaises(AccessError):
            activity.with_user(self.user_manager).write({"summary": "Take it back"})

    # ------------------------------------------------------------------
    # nobody assigned: the restriction must not apply
    # ------------------------------------------------------------------

    def test_restricted_activity_without_assignee_can_be_written(self):
        """Unassigned activities stay editable under the standard rules.

        ``user_id`` is optional since 19.0. Restricting an activity nobody is
        responsible for would lock it for everybody, forever, not even
        leaving a way to assign somebody to it.
        """
        activity = self._create_activity(self.activity_type_restricted, False)
        self.assertFalse(activity.user_id)

        activity.with_user(self.user_manager).write({"user_id": self.user_assigned.id})

        self.assertEqual(activity.user_id, self.user_assigned)

    def test_restricted_activity_without_assignee_can_be_unlinked(self):
        """Unassigned restricted activities can still be deleted."""
        activity = self._create_activity(self.activity_type_restricted, False)

        activity.with_user(self.user_manager).unlink()

        self.assertFalse(activity.exists())

    # ------------------------------------------------------------------
    # can_write: what hides the buttons in the chatter
    # ------------------------------------------------------------------

    def test_can_write_reflects_the_restriction(self):
        """Core hides the chatter buttons based on can_write."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned
        )
        self.env.invalidate_all()

        self.assertTrue(activity.with_user(self.user_assigned).can_write)
        self.env.invalidate_all()
        self.assertFalse(activity.with_user(self.user_manager).can_write)

    def test_restrict_field_default_value(self):
        """The restriction flag defaults to False."""
        activity_type = self.env["mail.activity.type"].create(
            {
                "name": "Default Activity Type",
            }
        )

        self.assertFalse(activity_type.can_write_restrict)
