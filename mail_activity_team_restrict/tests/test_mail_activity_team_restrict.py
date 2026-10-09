"""Tests for mail_activity_team_restrict."""

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user


class MailActivityTeamRestrictTest(TransactionCase):
    """Test cases for team-based access on restricted activities."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})
        cls.partner_model = cls.env["ir.model"]._get("res.partner")

        cls.user_assigned = new_test_user(
            cls.env,
            login="assigned@example.com",
            name="Assigned User",
            groups="base.group_user",
        )
        cls.user_team_member_1 = new_test_user(
            cls.env,
            login="member1@example.com",
            name="Team Member 1",
            groups="base.group_user",
        )
        cls.user_team_member_2 = new_test_user(
            cls.env,
            login="member2@example.com",
            name="Team Member 2",
            groups="base.group_user",
        )
        # Write access on res.partner makes core mail grant write on the
        # activities of that partner. Without it the standard Odoo rules
        # already stop this user and the tests below could not tell this
        # module and plain Odoo apart.
        cls.user_outsider = new_test_user(
            cls.env,
            login="outsider@example.com",
            name="Outsider User",
            groups="base.group_user,base.group_partner_manager",
        )

        cls.activity_type_unrestricted = cls.env["mail.activity.type"].create(
            {
                "name": "Follow Up (No Team)",
                "can_write_restrict": False,
            }
        )

        cls.activity_type_restricted = cls.env["mail.activity.type"].create(
            {
                "name": "Follow Up (Restrict Team)",
                "can_write_restrict": True,
            }
        )

        cls.team = cls.env["mail.activity.team"].create(
            {
                "name": "Restricted Team",
                "member_ids": [
                    Command.set(
                        [
                            cls.user_assigned.id,
                            cls.user_team_member_1.id,
                            cls.user_team_member_2.id,
                        ]
                    )
                ],
                "user_id": cls.user_assigned.id,
            }
        )

    @classmethod
    def _create_activity(cls, activity_type, user=None, team=None):
        values = {
            "activity_type_id": activity_type.id,
            "res_model_id": cls.partner_model.id,
            "res_id": cls.partner.id,
            "date_deadline": "2026-12-31",
        }
        if team:
            values["team_id"] = team.id
            if user:
                # mail_activity_team drops user_id from the values when a team
                # is given; the assignee has to be passed as team_user_id.
                values["team_user_id"] = user.id
        elif user:
            values["user_id"] = user.id
        activity = cls.env["mail.activity"].create(values)
        if not team and activity.team_id:
            # team_id is computed and gets filled in automatically when the
            # assignee belongs to a team. Clear it for the no-team cases.
            activity.sudo().team_id = False
        return activity

    # ------------------------------------------------------------------
    # a team is set and somebody is assigned
    # ------------------------------------------------------------------

    def test_activity_write_no_restriction(self):
        """Activities without the flag keep the default access behavior."""
        activity = self._create_activity(
            self.activity_type_unrestricted, self.user_assigned, self.team
        )

        activity.with_user(self.user_assigned).write(
            {"summary": "Updated by assigned user"}
        )

        self.assertEqual(activity.summary, "Updated by assigned user")

    def test_activity_write_restrict_only_assigned_user(self):
        """Assigned users may edit restricted activities."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned, self.team
        )
        self.assertEqual(activity.user_id, self.user_assigned)

        activity.with_user(self.user_assigned).write(
            {"summary": "Updated by assigned user"}
        )

        self.assertEqual(activity.summary, "Updated by assigned user")

    def test_activity_write_restrict_allows_team_member(self):
        """Team members may edit restricted activities when a team is assigned."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned, self.team
        )

        activity.with_user(self.user_team_member_1).write(
            {"summary": "Updated by team member"}
        )

        self.assertEqual(activity.summary, "Updated by team member")

    def test_activity_write_restrict_denies_outsider(self):
        """Users outside the assigned team remain blocked."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned, self.team
        )

        with self.assertRaises(AccessError):
            activity.with_user(self.user_outsider).write(
                {"summary": "Updated by outsider"}
            )

    def test_activity_write_no_restriction_allows_outsider(self):
        """Counter test: without the flag that same outsider may write."""
        activity = self._create_activity(
            self.activity_type_unrestricted, self.user_assigned, self.team
        )

        activity.with_user(self.user_outsider).write({"summary": "Updated"})

        self.assertEqual(activity.summary, "Updated")

    # ------------------------------------------------------------------
    # a team is set and nobody is assigned
    #
    # mail_activity_restrict leaves activities without an assigned user
    # alone. A team is a responsible on its own, so the restriction has to
    # apply here even though user_id is empty.
    # ------------------------------------------------------------------

    def test_unassigned_team_activity_allows_team_member(self):
        """Team members may edit a team activity that has no assignee."""
        activity = self._create_activity(self.activity_type_restricted, team=self.team)
        self.assertFalse(activity.user_id)
        self.assertEqual(activity.team_id, self.team)

        activity.with_user(self.user_team_member_1).write(
            {"summary": "Updated by team member"}
        )

        self.assertEqual(activity.summary, "Updated by team member")

    def test_unassigned_team_activity_denies_outsider(self):
        """Users outside the team may not edit a team activity without assignee."""
        activity = self._create_activity(self.activity_type_restricted, team=self.team)
        self.assertFalse(activity.user_id)

        with self.assertRaises(AccessError):
            activity.with_user(self.user_outsider).write(
                {"summary": "Updated by outsider"}
            )

    def test_unassigned_team_activity_denies_outsider_mark_done(self):
        """The same holds for completing the activity."""
        activity = self._create_activity(self.activity_type_restricted, team=self.team)

        with self.assertRaises(AccessError):
            activity.with_user(self.user_outsider).action_done()

        self.assertNotEqual(activity.state, "done")

    def test_unassigned_team_activity_denies_outsider_unlink(self):
        """The same holds for deleting the activity."""
        activity = self._create_activity(self.activity_type_restricted, team=self.team)

        with self.assertRaises(AccessError):
            activity.with_user(self.user_outsider).unlink()

        self.assertTrue(activity.exists())

    def test_unassigned_team_activity_no_restriction_allows_outsider(self):
        """Counter test: without the flag the outsider may write.

        Together with the test above this pins down that the restriction, and
        not a standard Odoo rule, is what stops the outsider.
        """
        activity = self._create_activity(
            self.activity_type_unrestricted, team=self.team
        )

        activity.with_user(self.user_outsider).write({"summary": "Updated"})

        self.assertEqual(activity.summary, "Updated")

    # ------------------------------------------------------------------
    # nobody responsible at all
    # ------------------------------------------------------------------

    def test_activity_without_user_and_team_is_not_restricted(self):
        """Without an assignee and without a team the standard rules apply.

        Restricting such an activity would leave it uneditable for everybody,
        with no way to assign somebody to it.
        """
        activity = self._create_activity(self.activity_type_restricted)
        self.assertFalse(activity.user_id)
        self.assertFalse(activity.team_id)

        activity.with_user(self.user_outsider).write({"summary": "Updated"})

        self.assertEqual(activity.summary, "Updated")

    # ------------------------------------------------------------------
    # no team: the base module decides on its own
    # ------------------------------------------------------------------

    def test_activity_write_restrict_without_team_denies_outsider(self):
        """Restricted activities without a team still require the assignee."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned
        )
        self.assertFalse(activity.team_id)

        with self.assertRaises(AccessError):
            activity.with_user(self.user_outsider).write(
                {"summary": "Updated by outsider"}
            )

    def test_activity_write_restrict_without_team_denies_team_member(self):
        """Team membership does not help when the activity has no team."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned
        )

        with self.assertRaises(AccessError):
            activity.with_user(self.user_team_member_1).write(
                {"summary": "Updated by team member"}
            )

    # ------------------------------------------------------------------
    # done / unlink with a team
    # ------------------------------------------------------------------

    def test_activity_action_done_respects_team_restriction(self):
        """Team members may mark restricted activities as done."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned, self.team
        )

        activity.with_user(self.user_team_member_1).action_done()

        self.assertEqual(activity.state, "done")

    def test_activity_action_done_denies_outsider(self):
        """Users outside the team cannot mark restricted activities as done."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned, self.team
        )

        with self.assertRaises(AccessError):
            activity.with_user(self.user_outsider).action_done()

        self.assertNotEqual(activity.state, "done")

    # ------------------------------------------------------------------
    # changing the team
    # ------------------------------------------------------------------

    def test_activity_team_change_updates_allowed_members(self):
        """Changing the activity team updates who may edit it."""
        activity = self._create_activity(
            self.activity_type_restricted, self.user_assigned, self.team
        )
        other_team = self.env["mail.activity.team"].create(
            {
                "name": "Other Team",
                "member_ids": [
                    Command.set([self.user_assigned.id, self.user_team_member_2.id])
                ],
                "user_id": self.user_assigned.id,
            }
        )

        activity.with_user(self.user_team_member_1).write(
            {"summary": "Updated by member 1"}
        )
        activity.with_user(self.user_assigned).write({"team_id": other_team.id})

        with self.assertRaises(AccessError):
            activity.with_user(self.user_team_member_1).write(
                {"summary": "Should fail"}
            )

        activity.with_user(self.user_team_member_2).write(
            {"summary": "Updated by member 2"}
        )

        self.assertEqual(activity.summary, "Updated by member 2")
