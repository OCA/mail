# Copyright 2018-22 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from datetime import date

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestMailActivityTeam(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        # Start from a clean slate
        cls.env["mail.activity.team"].search([]).unlink()
        # Create Users
        cls.employee = cls.env["res.users"].create(
            {
                "company_id": cls.env.ref("base.main_company").id,
                "name": "Employee",
                "login": "csu",
                "email": "crmuser@yourcompany.com",
                "group_ids": [
                    Command.set(
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("base.group_partner_manager").id,
                        ],
                    )
                ],
            }
        )
        cls.employee2 = cls.env["res.users"].create(
            {
                "company_id": cls.env.ref("base.main_company").id,
                "name": "Employee 2",
                "login": "csu2",
                "email": "crmuser2@yourcompany.com",
                "group_ids": [Command.set([cls.env.ref("base.group_user").id])],
            }
        )
        cls.employee3 = cls.env["res.users"].create(
            {
                "company_id": cls.env.ref("base.main_company").id,
                "name": "Employee 3",
                "login": "csu3",
                "email": "crmuser3@yourcompany.com",
                "group_ids": [Command.set([cls.env.ref("base.group_user").id])],
            }
        )
        # Create Activity Types
        cls.activity1 = cls.env["mail.activity.type"].create(
            {
                "name": "Initial Contact",
                "delay_count": 5,
                "delay_unit": "days",
                "summary": "ACT 1 : Presentation, barbecue, ... ",
                "res_model": "res.partner",
            }
        )
        cls.activity2 = cls.env["mail.activity.type"].create(
            {
                "name": "Call for Demo",
                "delay_count": 6,
                "delay_unit": "days",
                "summary": "ACT 2 : I want to show you my ERP !",
                "res_model": "res.partner",
            }
        )
        # Create Teams and Activities
        cls.partner_client = cls.env["res.partner"].create({"name": "Test Partner"})
        cls.partner_ir_model = cls.env["ir.model"]._get("res.partner")
        cls.act1 = (
            cls.env["mail.activity"]
            .with_user(cls.employee)
            .create(
                {
                    "activity_type_id": cls.activity1.id,
                    "note": "Partner activity 1.",
                    "res_id": cls.partner_client.id,
                    "res_model_id": cls.partner_ir_model.id,
                    "user_id": cls.employee.id,
                }
            )
        )
        cls.team1 = cls.env["mail.activity.team"].create(
            {
                "name": "Team 1",
                "res_model_ids": [Command.set([cls.partner_ir_model.id])],
                "member_ids": [Command.set([cls.employee.id])],
            }
        )
        cls.team2 = cls.env["mail.activity.team"].create(
            {
                "name": "Team 2",
                "res_model_ids": [Command.set([cls.partner_ir_model.id])],
                "member_ids": [Command.set([cls.employee.id, cls.employee2.id])],
                "notify_members": True,
            }
        )
        cls.act2 = (
            cls.env["mail.activity"]
            .with_user(cls.employee)
            .sudo()
            .create(
                {
                    "activity_type_id": cls.activity2.id,
                    "note": "Partner activity 2.",
                    "res_id": cls.partner_client.id,
                    "res_model_id": cls.partner_ir_model.id,
                    "user_id": cls.employee.id,
                }
            )
        )
        cls.schedule_act2 = (
            cls.env["mail.activity.schedule"]
            .with_user(cls.employee)
            .with_context(
                active_model=cls.partner_client._name,
                active_ids=cls.partner_client.ids,
                default_activity_user_id=cls.employee.id,
            )
            .create(
                {
                    "activity_type_id": cls.activity2.id,
                    "note": "Partner activity 2.",
                }
            )
        )

    def test_activity_members(self):
        self.team1.member_ids |= self.employee2
        self.partner_client.invalidate_recordset()
        self.assertIn(self.employee2, self.partner_client.activity_team_user_ids)
        self.assertIn(self.employee, self.partner_client.activity_team_user_ids)
        self.assertEqual(
            self.partner_client,
            self.env["res.partner"].search(
                [("activity_team_user_ids", "=", self.employee.id)]
            ),
        )

    def test_team_and_user_onchange(self):
        with self.assertRaises(ValidationError):
            self.team1.member_ids = [(3, self.employee.id)]
            self.act2.team_id = self.team1
            self.act2.user_id = self.employee

    def test_missing_activities(self):
        self.assertFalse(self.act1.team_id, "Error: Activity 1 should not have a team.")
        self.assertEqual(self.team1.count_missing_activities, 1)
        self.team1.assign_team_to_unassigned_activities()
        self.team1._compute_missing_activities()
        self.assertEqual(self.team1.count_missing_activities, 0)
        self.assertEqual(self.act1.team_id, self.team1)

    def test_leader_onchange(self):
        self.team2.user_id = self.employee3
        self.team2._onchange_user_id()
        self.assertTrue(self.employee3 in self.team2.member_ids)

    def test_activity_onchanges_keep_user(self):
        self.assertEqual(
            self.act2.team_id, self.team1, "Error: Activity 2 should have Team 1."
        )
        with Form(self.act2) as form:
            form.team_id = self.env["mail.activity.team"]
            self.assertEqual(form.user_id, self.employee)

    def test_activity_onchanges_user_no_member_team(self):
        self.assertEqual(
            self.act2.team_id, self.team1, "Error: Activity 2 should have Team 1."
        )
        with self.assertRaises(
            AssertionError, msg="can't write on invisible field user_id"
        ):
            with Form(self.act2) as form:
                form.user_id = self.employee2

    def test_activity_onchanges_user_no_team(self):
        self.assertEqual(
            self.act2.team_id, self.team1, "Error: Activity 2 should have Team 1."
        )
        with Form(self.act2) as form:
            form.team_id = self.env["mail.activity.team"]
            form.user_id = self.employee2
            self.assertEqual(form.team_id, self.team2)

    def test_activity_onchanges_team_no_member(self):
        self.assertEqual(
            self.act2.team_id, self.team1, "Error: Activity 2 should have Team 1."
        )
        self.team2.user_id = False
        self.team2.member_ids = False
        with Form(self.act2) as form:
            form.team_id = self.team2
            self.assertFalse(form.user_id)

    def test_activity_onchanges_team_different_member(self):
        self.assertEqual(
            self.act2.team_id, self.team1, "Error: Activity 2 should have Team 1."
        )
        self.team2.user_id = self.employee2
        self.team2.member_ids = self.employee2
        with Form(self.act2) as form:
            form.team_id = self.team2
            self.assertEqual(form.user_id, self.employee2)

    def test_activity_onchanges_team_different_member_no_leader(self):
        self.assertEqual(
            self.act2.team_id, self.team1, "Error: Activity 2 should have Team 1."
        )
        self.team2.user_id = False
        self.team2.member_ids = self.employee2
        with Form(self.act2) as form:
            form.team_id = self.team2
            self.assertEqual(form.user_id, self.employee2)

    def test_activity_onchanges_activity_type_set_team(self):
        self.assertEqual(
            self.act2.team_id, self.team1, "Error: Activity 2 should have Team 1."
        )
        self.activity1.default_team_id = self.team2
        self.assertEqual(self.act2.activity_type_id, self.activity2)
        with Form(self.act2) as form:
            form.activity_type_id = self.activity1
            self.assertEqual(form.team_id, self.team2)

    def test_activity_onchanges_activity_type_no_team(self):
        self.assertEqual(
            self.act2.team_id, self.team1, "Error: Activity 2 should have Team 1."
        )
        self.assertEqual(self.act2.activity_type_id, self.activity2)
        with Form(self.act2) as form:
            form.activity_type_id = self.activity1
            self.assertEqual(form.team_id, self.team1)

    ### Test mail.activity.schedule onchange / compute functionality, analogous
    ### to the mail.activity tests above.
    def test_schedule_activity_onchanges_keep_user(self):
        self.assertEqual(
            self.schedule_act2.activity_team_id,
            self.team1,
            "Error: wizard should have Team 1.",
        )
        with Form(self.schedule_act2) as form:
            form.activity_team_id = self.env["mail.activity.team"]
            self.assertEqual(form.activity_user_id, self.employee)

    def test_schedule_activity_onchanges_user_no_member_team(self):
        self.assertEqual(
            self.schedule_act2.activity_team_id,
            self.team1,
            "Error: Activity 2 should have Team 1.",
        )
        with self.assertRaises(
            AssertionError, msg="can't write on invisible field user_id"
        ):
            with Form(self.schedule_act2) as form:
                form.activity_user_id = self.employee2

    def test_schedule_activity_onchanges_user_no_team(self):
        self.assertEqual(
            self.schedule_act2.activity_team_id,
            self.team1,
            "Error: Activity 2 should have Team 1.",
        )
        with Form(self.schedule_act2) as form:
            form.activity_team_id = self.env["mail.activity.team"]
            form.activity_user_id = self.employee2
            self.assertEqual(form.activity_team_id, self.team2)

    def test_schedule_activity_onchanges_team_no_member(self):
        self.assertEqual(
            self.schedule_act2.activity_team_id,
            self.team1,
            "Error: Activity 2 should have Team 1.",
        )
        self.team2.user_id = False
        self.team2.member_ids = False
        with Form(self.schedule_act2) as form:
            form.activity_team_id = self.team2
            self.assertFalse(form.activity_user_id)

    def test_schedule_activity_onchanges_team_different_member(self):
        self.assertEqual(
            self.schedule_act2.activity_team_id,
            self.team1,
            "Error: Activity 2 should have Team 1.",
        )
        self.team2.user_id = self.employee2
        self.team2.member_ids = self.employee2
        with Form(self.schedule_act2) as form:
            form.activity_team_id = self.team2
            self.assertEqual(form.activity_user_id, self.employee2)

    def test_schedule_activity_onchanges_team_different_member_no_leader(self):
        self.assertEqual(
            self.schedule_act2.activity_team_id,
            self.team1,
            "Error: Activity 2 should have Team 1.",
        )
        self.team2.user_id = False
        self.team2.member_ids = self.employee2
        with Form(self.schedule_act2) as form:
            form.activity_team_id = self.team2
            self.assertEqual(form.activity_user_id, self.employee2)

    def test_schedule_activity_onchanges_activity_type_set_team(self):
        self.assertEqual(
            self.schedule_act2.activity_team_id,
            self.team1,
            "Error: Activity 2 should have Team 1.",
        )
        self.activity1.default_team_id = self.team2
        self.assertEqual(self.schedule_act2.activity_type_id, self.activity2)
        with Form(self.schedule_act2) as form:
            form.activity_type_id = self.activity1
            self.assertEqual(form.activity_team_id, self.team2)

    def test_schedule_activity_onchanges_activity_type_no_team(self):
        self.assertEqual(
            self.schedule_act2.activity_team_id,
            self.team1,
            "Error: Activity 2 should have Team 1.",
        )
        self.assertEqual(self.schedule_act2.activity_type_id, self.activity2)
        with Form(self.schedule_act2) as form:
            form.activity_type_id = self.activity1
            self.assertEqual(form.activity_team_id, self.team1)

    def test_activity_constrain(self):
        with self.assertRaises(ValidationError):
            self.act2.write({"user_id": self.employee2.id, "team_id": self.team1.id})

    def test_schedule_activity(self):
        """Correctly assign teams to auto scheduled activities. Those won't
        trigger onchanges and could raise constraints and team missmatches"""
        partner_record = self.employee.partner_id.with_user(self.employee.id)
        activity = partner_record.activity_schedule(
            user_id=self.employee2.id,
            activity_type_id=self.env.ref("mail.mail_activity_data_call").id,
        )
        self.assertEqual(activity.team_id, self.team2)

    def test_schedule_activity_default_team(self):
        """Correctly assign teams to auto scheduled activities. Those won't
        trigger onchanges and could raise constraints and team missmatches"""
        partner_record = self.employee.partner_id.with_user(self.employee.id)
        self.env.ref("mail.mail_activity_data_call").default_team_id = self.team2
        activity = partner_record.activity_schedule(
            act_type_xmlid="mail.mail_activity_data_call",
        )
        self.assertEqual(activity.team_id, self.team2)
        # As we are in a 'team activity' context, the user should not be set
        self.assertEqual(activity.user_id, self.env["res.users"])

    def test_schedule_activity_default_team_no_user(self):
        """Correctly assign teams to auto scheduled activities. Those won't
        trigger onchanges and could raise constraints and team missmatches"""
        partner_record = self.employee.partner_id.with_user(self.employee.id)
        self.activity2.default_team_id = self.team2
        self.team2.member_ids = self.employee2
        activity = partner_record.activity_schedule(
            activity_type_id=self.activity2.id,
        )
        self.assertEqual(activity.team_id, self.team2)
        # As we are in a 'team activity' context, the user should not be set
        self.assertEqual(activity.user_id, self.env["res.users"])

    def test_schedule_activity_no_default_team(self):
        """If there are no teams, activities can still be scheduled for users"""
        self.env["mail.activity.team"].search([]).unlink()
        partner_record = self.employee.partner_id.with_user(self.employee.id)
        activity = partner_record.activity_schedule(
            activity_type_id=self.activity2.id,
            user_id=self.employee2.id,
        )
        self.assertFalse(activity.team_id)
        self.assertEqual(activity.user_id, self.employee2)

    def test_activity_count(self):
        res = (
            self.env["res.users"]
            .with_user(self.employee.id)
            .with_context(**{"team_activities": True})
            ._get_activity_groups()
        )
        self.assertEqual(res[0]["total_count"], 0)
        self.assertEqual(res[0]["today_count"], 1)
        partner_record = self.employee.partner_id.with_user(self.employee.id)
        self.activity2.default_team_id = self.team2
        activity = partner_record.activity_schedule(
            activity_type_id=self.activity2.id, user_id=self.employee2.id
        )
        activity.flush_recordset()
        res = (
            self.env["res.users"]
            .with_user(self.employee.id)
            .with_context(**{"team_activities": True})
            ._get_activity_groups()
        )
        self.assertEqual(res[0]["total_count"], 1)
        self.assertEqual(res[0]["today_count"], 2)
        res = self.env["res.users"].with_user(self.employee.id)._get_activity_groups()
        self.assertEqual(res[0]["total_count"], 1)

    def test_activity_schedule_next(self):
        self.activity1.write(
            {
                "default_team_id": self.team1.id,
                "triggered_next_type_id": self.activity2.id,
            }
        )
        self.activity2.default_team_id = self.team2
        self.team2.member_ids = self.employee2
        partner_record = self.employee.partner_id.with_user(self.employee.id)
        activity = partner_record.activity_schedule(activity_type_id=self.activity1.id)
        activity.flush_recordset()
        _messages, next_activities = activity._action_done()
        self.assertTrue(next_activities)
        self.assertEqual(next_activities.team_id, self.team2)
        # As we are in a 'team activity' context, the user should not be set
        self.assertEqual(next_activities.user_id, self.env["res.users"])

    def test_mail_activity_schedule_wizard(self):
        self.activity1.default_team_id = self.team1
        wizard_form = Form(
            self.env["mail.activity.schedule"].with_context(
                active_ids=self.partner_client.ids,
                active_model=self.partner_client._name,
            )
        )
        wizard_form.activity_type_id = self.activity1
        # The activity's default team is set, and its member is the assigned user
        self.assertEqual(wizard_form.activity_team_id, self.team1)
        self.assertEqual(wizard_form.activity_team_user_id, self.employee)

        # Assign a team with a default member
        self.team2.user_id = self.employee2
        wizard_form.activity_team_id = self.team2
        # Original team user is kept because it is also a member of the new team
        self.assertEqual(wizard_form.activity_team_user_id, self.employee)

        # Reset some values and assign the team with the default user again
        wizard_form.activity_team_user_id = self.env["res.users"]
        wizard_form.activity_team_id = self.team2
        # Now the team user is the default user of the team
        self.assertEqual(wizard_form.activity_team_user_id, self.employee2)

        other_team = self.env["mail.activity.team"].create(
            {
                "name": "Team 3",
                "member_ids": [
                    Command.link(self.employee.id),
                    Command.link(self.employee3.id),
                ],
            },
        )
        wizard_form.activity_team_id = other_team
        # Employee 2 is not a member of the new team, so team user is reset
        self.assertFalse(wizard_form.activity_team_user_id)

        # Set one of the members of the team and schedule the activity
        wizard_form.activity_team_user_id = self.employee3

        activities = self.partner_client.activity_ids
        # Schedule the activity
        wizard_form.save().action_schedule_activities()
        activity = self.partner_client.activity_ids - activities
        self.assertRecordValues(
            activity,
            [
                {
                    "activity_type_id": self.activity1.id,
                    "team_id": other_team.id,
                    "user_id": self.employee3.id,
                },
            ],
        )

    def test_schedule_activity_from_server_action(self):
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        action = self.env["ir.actions.server"].create(
            {
                "name": "Test Server Action",
                "model_id": self.partner_ir_model.id,
                "state": "next_activity",
                "activity_type_id": self.activity1.id,
                "activity_user_type": "specific",
                "activity_user_id": self.employee.id,
                "activity_team_id": self.team1.id,
            }
        )
        action.with_context(active_model=partner._name, active_ids=partner.ids).run()
        self.assertEqual(partner.activity_ids[-1].team_id, self.team1)
        action.activity_team_id = self.team2
        action.with_context(active_model=partner._name, active_ids=partner.ids).run()
        self.assertEqual(partner.activity_ids[-1].team_id, self.team2)

    def test_server_action_onchanges_activity_team_id_activity_user_id(self):
        self.team1.user_id = self.team1.member_ids[0]
        server_action = self.env["ir.actions.server"].create(
            {
                "name": "Test Server Action 2",
                "model_id": self.partner_ir_model.id,
                "state": "next_activity",
                "activity_type_id": self.activity2.id,
                "activity_user_type": "specific",
                "activity_user_id": self.employee.id,
            }
        )
        with Form(server_action) as form:
            form.activity_team_id = self.team1
            self.assertEqual(form.activity_user_id, self.team1.user_id)

    def test_my_activity_date_deadline(self):
        """This test case checks
        - if the team activities are properly filtered
        """
        today = date.today()
        self.act2.write(
            {
                "user_id": False,
                "team_id": self.team1.id,
                "date_deadline": today,
            }
        )
        partner = (
            self.env["res.partner"]
            .with_context(team_activities=True)
            .with_user(self.employee.id)
            .search([("my_activity_date_deadline", "=", today)])
        )
        self.assertEqual(partner, self.partner_client)
        self.assertEqual(partner.my_activity_date_deadline, today)

    def _web_search_read_to_ids(self, domain, context=None):
        """Return web_search_read results as a set of ids"""
        if context is None:
            context = {}
        res = (
            self.env["res.partner"]
            .with_context(**context)
            .web_search_read(
                domain,
                {"id": {}},
            )
        )
        return set(record["id"] for record in res["records"])

    def test_web_search_read(self):
        """Test the domain mangling of web_search_read"""
        # Create a non-team activity for our second employee, for a second partner
        self.team1.member_ids |= self.employee2
        partner2 = self.partner_client.copy()
        self.employee2.group_ids += self.env.ref("base.group_partner_manager")

        # Craft the activity without a team
        act3 = (
            self.env["mail.activity"]
            .with_user(self.employee2)
            .create(
                {
                    "activity_type_id": self.activity1.id,
                    "note": "Partner activity 3.",
                    "res_id": partner2.id,
                    "res_model_id": self.partner_ir_model.id,
                    "team_user_id": self.employee2.id,
                    "user_id": self.employee2.id,
                    "team_id": False,
                }
            )
        )
        self.assertFalse(act3.team_id)

        # A regular search retrieves this activity
        self.assertEqual(
            self._web_search_read_to_ids(
                [("activity_user_id", "=", self.employee2.id)]
            ),
            set(partner2.ids),
        )

        # Searching with magic context key retrieves team activities.
        self.assertEqual(
            self._web_search_read_to_ids(
                [("activity_user_id", "=", self.employee2.id)],
                {"team_activities": True},
            ),
            set(self.partner_client.ids),
        )

    def test_notify_members_disabled(self):
        """Test that when notify_members is False, only assigned user is notified."""
        # Create an activity for the team
        self.team1.member_ids = [
            (6, 0, [self.employee.id, self.employee2.id, self.employee3.id])
        ]
        activity = self.env["mail.activity"].create(
            {
                "activity_type_id": self.activity1.id,
                "note": "Test activity without notify_members.",
                "res_id": self.partner_client.id,
                "res_model_id": self.partner_ir_model.id,
                "team_user_id": self.employee.id,
                "team_id": self.team1.id,
            }
        )

        # Count initial messages for team members
        initial_msg_count_emp = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee.partner_id.id])]
            )
        )
        initial_msg_count_emp2 = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee2.partner_id.id])]
            )
        )
        initial_msg_count_emp3 = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee3.partner_id.id])]
            )
        )

        # Call action_notify
        activity.action_notify()

        # Verify only the assigned user (employee) received a notification
        final_msg_count_emp = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee.partner_id.id])]
            )
        )
        final_msg_count_emp2 = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee2.partner_id.id])]
            )
        )
        final_msg_count_emp3 = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee3.partner_id.id])]
            )
        )

        self.assertGreater(
            final_msg_count_emp,
            initial_msg_count_emp,
            "Assigned user should receive notification",
        )
        self.assertEqual(
            final_msg_count_emp2,
            initial_msg_count_emp2,
            "Non-assigned team member should not receive notification",
        )
        self.assertEqual(
            final_msg_count_emp3,
            initial_msg_count_emp3,
            "Non-assigned team member should not receive notification",
        )

    def test_notify_members_enabled(self):
        """Test that when notify_members is True, all team members are notified."""
        # Create an activity for the team
        self.team2.member_ids = [
            (6, 0, [self.employee.id, self.employee2.id, self.employee3.id])
        ]
        activity = self.env["mail.activity"].create(
            {
                "activity_type_id": self.activity1.id,
                "note": "Test activity with notify_members enabled.",
                "res_id": self.partner_client.id,
                "res_model_id": self.partner_ir_model.id,
                "team_user_id": self.employee.id,
                "team_id": self.team2.id,
            }
        )

        # Count initial messages for team members
        initial_msg_count_emp = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee.partner_id.id])]
            )
        )
        initial_msg_count_emp2 = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee2.partner_id.id])]
            )
        )
        initial_msg_count_emp3 = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee3.partner_id.id])]
            )
        )

        # Call action_notify
        activity.action_notify()

        # Verify all team members received notifications
        final_msg_count_emp = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee.partner_id.id])]
            )
        )
        final_msg_count_emp2 = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee2.partner_id.id])]
            )
        )
        final_msg_count_emp3 = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee3.partner_id.id])]
            )
        )

        self.assertGreater(
            final_msg_count_emp,
            initial_msg_count_emp,
            "Assigned user should receive notification",
        )
        self.assertGreater(
            final_msg_count_emp2,
            initial_msg_count_emp2,
            "Team member 2 should receive notification",
        )
        self.assertGreater(
            final_msg_count_emp3,
            initial_msg_count_emp3,
            "Team member 3 should receive notification",
        )

    def test_notify_members_no_duplicate_for_assigned_user(self):
        """Test that the assigned user doesn't get duplicate notifications."""
        # Create an activity assigned to employee (who is in the team)
        activity = self.env["mail.activity"].create(
            {
                "activity_type_id": self.activity1.id,
                "note": "Test no duplicate notifications.",
                "res_id": self.partner_client.id,
                "res_model_id": self.partner_ir_model.id,
                "user_id": self.employee.id,
                "team_id": self.team2.id,
            }
        )

        # Count initial messages for the assigned user
        initial_msg_count = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee.partner_id.id])]
            )
        )

        # Call action_notify
        activity.action_notify()

        # Verify the assigned user received exactly one new notification
        final_msg_count = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee.partner_id.id])]
            )
        )

        # The assigned user should receive only 1 notification (from parent method)
        # not 2 (parent + team member notification)
        self.assertEqual(
            final_msg_count - initial_msg_count,
            1,
            "Assigned user should receive exactly one notification, not duplicates",
        )

    def test_notify_members_activity_without_team(self):
        """Test that activities without a team still work correctly."""
        # Create an activity without a team
        activity = self.env["mail.activity"].create(
            {
                "activity_type_id": self.activity1.id,
                "note": "Test activity without team.",
                "res_id": self.partner_client.id,
                "res_model_id": self.partner_ir_model.id,
                "user_id": self.employee.id,
            }
        )

        # Count initial messages
        initial_msg_count = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee.partner_id.id])]
            )
        )

        # Call action_notify - should not raise any error
        activity.action_notify()

        # Verify the assigned user received a notification
        final_msg_count = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee.partner_id.id])]
            )
        )

        self.assertGreater(
            final_msg_count,
            initial_msg_count,
            "Assigned user should receive notification even without team",
        )

    def test_notify_members_activity_without_assigned_user(self):
        """Test that team notifications work when activity has no assigned user."""
        # Create an activity without an assigned user
        activity = self.env["mail.activity"].create(
            {
                "activity_type_id": self.activity1.id,
                "note": "Test activity without assigned user.",
                "res_id": self.partner_client.id,
                "res_model_id": self.partner_ir_model.id,
                "team_id": self.team2.id,
            }
        )

        # Count initial messages for team members
        initial_msg_count_emp = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee.partner_id.id])]
            )
        )
        initial_msg_count_emp2 = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee2.partner_id.id])]
            )
        )

        # Call action_notify
        activity.action_notify()

        # Verify all team members received notifications
        final_msg_count_emp = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee.partner_id.id])]
            )
        )
        final_msg_count_emp2 = len(
            self.env["mail.message"].search(
                [("partner_ids", "in", [self.employee2.partner_id.id])]
            )
        )

        self.assertGreater(
            final_msg_count_emp,
            initial_msg_count_emp,
            "Team member 1 should receive notification",
        )
        self.assertGreater(
            final_msg_count_emp2,
            initial_msg_count_emp2,
            "Team member 2 should receive notification",
        )

    def test_notify_no_duplicate_when_team_and_user_assigned_on_create(self):
        """
        Activity created by user A, assigned to team A (user B and C,
        notify_members=True) and explicitly to user B.
        Verifies that B and C are each notified exactly once through the full
        create flow.

        Setup:
        - employee = user A (creator, not in team)
        - team2: notify_members=True, members: employee2 (B) and employee3 (C)
        - Activity assigned to team2 AND employee2 (B) via team_user_id

        Expected: B gets 1 notification (from action_notify), C gets 1 notification
        (from action_notify_team) — no duplicate for C due to action_notify_team
        being called twice in create.
        """
        self.team2.write(
            {"member_ids": [(6, 0, [self.employee2.id, self.employee3.id])]}
        )
        partner = self.env["res.partner"].create(
            {"name": "Test No Dup On Create Partner"}
        )
        employee_b_pid = self.employee2.partner_id.id
        employee_c_pid = self.employee3.partner_id.id

        before_b = self.env["mail.message"].search_count(
            [("partner_ids", "in", [employee_b_pid])]
        )
        before_c = self.env["mail.message"].search_count(
            [("partner_ids", "in", [employee_c_pid])]
        )

        # User A (employee) creates activity for team A (team2) and assigns to user B
        self.env["mail.activity"].with_user(self.employee).create(
            {
                "activity_type_id": self.activity1.id,
                "note": "Dedup test: team + assigned user on create.",
                "res_id": partner.id,
                "res_model_id": self.partner_ir_model.id,
                "team_id": self.team2.id,
                "team_user_id": self.employee2.id,
            }
        )

        after_b = self.env["mail.message"].search_count(
            [("partner_ids", "in", [employee_b_pid])]
        )
        after_c = self.env["mail.message"].search_count(
            [("partner_ids", "in", [employee_c_pid])]
        )

        self.assertEqual(
            after_b - before_b,
            1,
            "User B (assigned user and team member) should be notified exactly once",
        )
        self.assertEqual(
            after_c - before_c,
            1,
            "User C (team member only) should be notified exactly once, not twice",
        )

    def test_mail_activity_plan_ui_logic(self):
        """Check team/team user consistency in plan template view"""
        plan = self.env["mail.activity.plan"].create(
            {
                "name": __name__,
                "res_model": "res.partner",
            }
        )
        self.activity1.default_team_id = self.team1
        template = self.env["mail.activity.plan.template"].create(
            {
                "summary": __name__,
                "responsible_type": "other",
                "responsible_id": self.employee3.id,
                "activity_type_id": self.activity1.id,
                "plan_id": plan.id,
                "sequence": 1,
                "delay_count": 1,
            }
        )
        # Team is not set by default
        self.assertFalse(template.activity_team_id)
        # If template is set to assign to team, default team of the activity is set
        template.responsible_type = "team"
        self.assertEqual(template.activity_team_id, self.team1)

        # Can't just remove the team without changing the assignment type
        with self.assertRaisesRegex(
            ValidationError,
            "Please enter an activity team",
        ):
            with self.env.cr.savepoint():
                template.activity_team_id = False

        # Team is reset if type is not team
        template.write(
            {
                "responsible_type": "other",
                "responsible_id": self.env.user.id,
            },
        )
        self.assertFalse(template.activity_team_id)

        # The default team user is set to the only member of the team
        template.write(
            {
                "responsible_type": "team",
                "activity_team_id": self.team1.id,
            }
        )
        self.assertEqual(template.activity_team_user_id, self.employee)
        # The responsible is reset if assignment is changed to team
        self.assertFalse(template.responsible_id)
        # Assign a team with a default member
        self.team2.user_id = self.employee2
        template.activity_team_id = self.team2
        # Original team user is kept because it is also a member of the new team
        self.assertEqual(template.activity_team_user_id, self.employee)
        # Team user is reset if team is reset
        template.write(
            {
                "responsible_type": "other",
                "responsible_id": self.env.user.id,
                "activity_team_id": False,
            },
        )
        self.assertFalse(template.activity_team_user_id)
        # Assign the team with the default user again
        template.write(
            {
                "responsible_type": "team",
                "activity_team_id": self.team2.id,
            },
        )
        # Now the team user is the default user of the team
        self.assertEqual(template.activity_team_user_id, self.employee2)

        other_team = self.env["mail.activity.team"].create(
            {
                "name": "Team 3",
                "member_ids": [
                    Command.link(self.employee.id),
                    Command.link(self.employee3.id),
                ],
            },
        )
        template.activity_team_id = other_team
        # Employee 2 is not a member of the new team, so team user is reset
        self.assertFalse(template.activity_team_user_id)

    def test_mail_activity_plan(self):
        """Activities for teams can be scheduled using an activity plan"""
        plan = self.env["mail.activity.plan"].create(
            {
                "name": __name__,
                "res_model": "res.partner",
            }
        )
        self.env["mail.activity.plan.template"].create(
            {
                "summary": __name__,
                "responsible_type": "other",
                "responsible_id": self.employee3.id,
                "activity_type_id": self.activity1.id,
                "plan_id": plan.id,
                "sequence": 1,
                "delay_count": 1,
            }
        )
        self.env["mail.activity.plan.template"].create(
            {
                "summary": __name__,
                "responsible_type": "team",
                "activity_team_id": self.team1.id,
                "activity_type_id": self.activity2.id,
                "plan_id": plan.id,
                "sequence": 2,
                "delay_count": 2,
            }
        )
        activities = self.partner_client.activity_ids

        wizard = (
            self.env["mail.activity.schedule"]
            .with_context(
                active_ids=self.partner_client.ids,
                active_model=self.partner_client._name,
            )
            .create(
                {
                    "plan_id": plan.id,
                    "plan_date": date.today(),
                }
            )
        )
        wizard.action_schedule_plan()
        new_activities = self.partner_client.activity_ids - activities
        self.assertRecordValues(
            new_activities,
            [
                {
                    "activity_type_id": self.activity2.id,
                    "team_id": self.team1.id,
                    "user_id": False,
                },
                {
                    "activity_type_id": self.activity1.id,
                    "team_id": False,
                    "user_id": self.employee3.id,
                },
            ],
        )

        # Coverage: _plan_filter_activity_templates_to_schedule will still
        # return both activities if called without special context key
        self.assertEqual(
            wizard._plan_filter_activity_templates_to_schedule(),
            plan.template_ids,
        )
        # or when upper frame inspection fails
        with self.assertLogs(
            "odoo.addons.mail_activity_team.wizard.mail_activity_schedule",
            level="WARNING",
        ) as log_catcher:
            self.assertEqual(
                wizard.with_context(
                    fire_team_activities=True,
                )._plan_filter_activity_templates_to_schedule(),
                plan.template_ids,
            )
            self.assertIn(
                "Could not find 'activity_descriptions' list in inspected frames",
                log_catcher.output[0],
            )
