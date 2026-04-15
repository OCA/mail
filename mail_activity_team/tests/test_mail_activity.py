from odoo import Command
from odoo.tests import Form, users

from odoo.addons.base.tests.common import BaseCommon


class TestMailActivity(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create Users
        cls.user = cls.env["res.users"].create(
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
                        ]
                    )
                ],
            }
        )
        cls.user2 = cls.env["res.users"].create(
            {
                "company_id": cls.env.ref("base.main_company").id,
                "name": "Employee 2",
                "login": "csu2",
                "email": "crmuser2@yourcompany.com",
                "group_ids": [Command.set([cls.env.ref("base.group_user").id])],
            }
        )
        cls.partner_ir_model = cls.env["ir.model"]._get("res.partner")
        cls.partner_client = cls.env["res.partner"].create({"name": "Test Partner"})
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

    @users("csu")
    def test_get_default_team_id_one_team_with_model(self):
        """Test _get_default_team_id correctly finds team with specified model_id"""
        # Create a team specific to res.partner model
        team_partner = (
            self.env["mail.activity.team"]
            .sudo()
            .create(
                {
                    "name": "Partner Team",
                    "res_model_ids": [Command.set([self.partner_ir_model.id])],
                    "member_ids": [Command.set([self.user.id])],
                }
            )
        )
        form_team_from_user = Form(
            self.env["mail.activity"].with_context(
                default_res_model="res.partner",
                default_res_id=self.partner_client.id,
            )
        )
        self.assertEqual(
            form_team_from_user.team_id,
            team_partner,
            "Should return the team matching the model_id",
        )
        activity = form_team_from_user.save()
        self.assertEqual(
            activity.team_id,
            team_partner,
            "Should return the team matching the model_id",
        )

    @users("csu")
    def test_get_default_team_id_one_team_without_model_restriction(self):
        """Test _get_default_team_id finds team without model restrictions"""
        # Create a team without model restrictions
        team_generic = (
            self.env["mail.activity.team"]
            .sudo()
            .create(
                {
                    "name": "Generic Team",
                    "res_model_ids": [Command.clear()],  # No model restrictions
                    "member_ids": [Command.set([self.user.id])],
                }
            )
        )
        # Test without a model - should find the generic team
        form_result_team = Form(self.env["mail.activity"])
        self.assertEqual(
            form_result_team.team_id,
            team_generic,
            "Should return team without model restrictions",
        )
        # Test with a model - still finds the generic team
        form_result_team_from_model = Form(
            self.env["mail.activity"].with_context(
                default_res_model="res.partner",
                default_res_id=self.partner_client.id,
            ),
        )
        self.assertEqual(
            form_result_team_from_model.team_id,
            team_generic,
            "Should return team without model restrictions",
        )

    def test_get_default_team_id_no_match(self):
        """Test _get_default_team_id returns empty when no team matches"""
        # Create a team for a specific model
        self.env["mail.activity.team"].sudo().create(
            {
                "name": "Users Team",
                "res_model_ids": [Command.set([self.partner_ir_model.id])],
                "member_ids": [Command.set([self.user.id])],
            }
        )
        # Search for a different user who is not a member
        form_result_team = Form(
            self.env["mail.activity"].with_context(
                default_res_model="res.partner",
                default_res_id=self.partner_client.id,
            )
        )
        form_result_team.user_id = self.user2
        self.assertFalse(
            form_result_team.team_id,
            "Should return empty recordset when user is not a team member",
        )
        activity = form_result_team.save()
        self.assertFalse(
            activity.team_id,
            "Should return empty recordset when user is not a team member",
        )

    def test_get_default_team_id_priority_model_match(self):
        """Test _get_default_team_id returns first matching team"""
        # Create two teams for the same model and user
        self.env["mail.activity.team"].create(
            {
                "name": "Team A",
                "res_model_ids": [Command.clear()],  # No model restrictions
                "member_ids": [Command.set([self.user.id])],
            }
        )
        team_b = self.env["mail.activity.team"].create(
            {
                "name": "Team B",
                "res_model_ids": [Command.set([self.partner_ir_model.id])],
                "member_ids": [Command.set([self.user.id])],
            }
        )
        # Test - should return the first match (based on search order)
        form_result_team = Form(
            self.env["mail.activity"].with_context(
                default_res_model_id=self.partner_ir_model.id,
                default_res_id=self.partner_client.id,
            )
        )
        form_result_team.user_id = self.user
        self.assertEqual(
            form_result_team.team_id,
            team_b,
            "Should return the team with model match",
        )
        activity = form_result_team.save()
        self.assertEqual(
            activity.team_id,
            team_b,
            "Should return the team with model match",
        )

    def test_create_activity_without_team_assigns_team_by_model_and_user(self):
        """Test creating activity with user_id but no team_id assigns default team"""
        # Clean up existing activities
        self.env["mail.activity"].search([]).unlink()
        # Create a team for the partner model
        team = self.env["mail.activity.team"].create(
            {
                "name": "Auto Assign Team",
                "res_model_ids": [Command.set([self.partner_ir_model.id])],
                "member_ids": [Command.set([self.user.id])],
            }
        )
        # Create an activity with team_user_id but no team_id
        activity = self.env["mail.activity"].create(
            {
                "activity_type_id": self.activity1.id,
                "note": "Test auto team assignment",
                "res_id": self.partner_client.id,
                "res_model_id": self.partner_ir_model.id,
                "team_user_id": self.user.id,
            }
        )
        # Verify team was not assigned
        self.assertEqual(
            activity.team_id,
            team,
            "Team should be selected by model and (team) user",
        )

    def test_create_activity_without_team_assigns_correct_team(self):
        """Test creating activity with user_id but no team_id assigns default team"""
        # Clean up existing activities
        self.env["mail.activity"].search([]).unlink()
        # Create a team for the partner model
        team_auto = self.env["mail.activity.team"].create(
            {
                "name": "Auto Assign Team",
                "res_model_ids": [Command.set([self.partner_ir_model.id])],
                "member_ids": [Command.set([self.user.id])],
            }
        )
        # Create an activity with user_id but no team_id
        activity = self.env["mail.activity"].create(
            {
                "activity_type_id": self.activity1.id,
                "note": "Test auto team assignment",
                "res_id": self.partner_client.id,
                "res_model_id": self.partner_ir_model.id,
                "user_id": self.user.id,
            }
        )
        # Verify team was automatically assigned
        self.assertEqual(
            activity.team_id,
            team_auto,
            "Team should be automatically assigned based on user and model",
        )

    def test_create_activity_with_team_false(self):
        """Test creating activity with user_id but no team_id assigns default team"""
        # Clean up existing activities
        self.env["mail.activity"].search([]).unlink()
        # Create a team for the partner model
        self.env["mail.activity.team"].create(
            {
                "name": "Auto Assign Team",
                "res_model_ids": [Command.set([self.partner_ir_model.id])],
                "member_ids": [Command.set([self.user.id])],
            }
        )
        # Create an activity with user_id but no team_id
        activity = self.env["mail.activity"].create(
            {
                "activity_type_id": self.activity1.id,
                "note": "Test auto team assignment",
                "res_id": self.partner_client.id,
                "res_model_id": self.partner_ir_model.id,
                "team_user_id": self.user.id,
                "team_id": False,  # Explicitly set team_id to False
            }
        )
        # Verify that no team was assigned
        self.assertFalse(
            activity.team_id,
            "Team should not be assigned when team_id is explicitly set to False",
        )

    def test_create_keeps_user_when_team_explicitly_false(self):
        """Explicit team_id=False must not drop an explicit assignee."""
        activity = (
            self.env["mail.activity"]
            .with_user(self.user)
            .sudo()
            .create(
                {
                    "activity_type_id": self.activity1.id,
                    "note": "Regression check: keep explicit assignee.",
                    "res_id": self.partner_client.id,
                    "res_model_id": self.partner_ir_model.id,
                    "user_id": self.user2.id,
                    "team_id": False,
                }
            )
        )
        self.assertFalse(activity.team_id)
        self.assertEqual(activity.user_id, self.user2)
