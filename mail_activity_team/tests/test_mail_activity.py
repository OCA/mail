from odoo import Command
from odoo.tests import users

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
                "groups_id": [
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
                "groups_id": [Command.set([cls.env.ref("base.group_user").id])],
            }
        )
        cls.partner_ir_model = cls.env["ir.model"]._get("res.partner")
        cls.partner_client = cls.env.ref("base.res_partner_1")
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
        # Test with model_id parameter - should find the team
        result_team_from_user = (
            self.env["mail.activity"]
            .with_context(default_res_model="res.partner")
            ._get_default_team_id(user_id=self.user.id)
        )
        self.assertEqual(
            result_team_from_user,
            team_partner,
            "Should return the team matching the model_id",
        )
        result_team = self.env["mail.activity"]._get_default_team_id(
            user_id=self.user.id, model_id=self.partner_ir_model.id
        )
        self.assertEqual(
            result_team,
            team_partner,
            "Should return the team matching the model_id",
        )
        result_team_from_model = self.env["mail.activity"]._get_default_team_id(
            model_id=self.partner_ir_model.id
        )
        self.assertEqual(
            result_team_from_model,
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
        # Test with a different model - should find the generic team
        user_ir_model = self.env["ir.model"]._get("res.users")
        result_team = self.env["mail.activity"]._get_default_team_id(
            user_id=self.user.id, model_id=user_ir_model.id
        )
        self.assertEqual(
            result_team,
            team_generic,
            "Should return team without model restrictions",
        )
        result_team_from_user = self.env["mail.activity"]._get_default_team_id(
            user_id=self.user.id
        )
        self.assertEqual(
            result_team_from_user,
            team_generic,
            "Should return team without model restrictions",
        )
        result_team_from_model = (
            self.env["mail.activity"]
            .with_context(default_res_model="res.partner")
            ._get_default_team_id(model_id=user_ir_model.id)
        )
        self.assertEqual(
            result_team_from_model,
            team_generic,
            "Should return team without model restrictions",
        )

    def test_get_default_team_id_no_match(self):
        """Test _get_default_team_id returns empty when no team matches"""
        # Create a team for a specific model
        user_ir_model = self.env["ir.model"]._get("res.users")
        self.env["mail.activity.team"].sudo().create(
            {
                "name": "Users Team",
                "res_model_ids": [Command.set([user_ir_model.id])],
                "member_ids": [Command.set([self.user.id])],
            }
        )
        # Search for a different user who is not a member
        result_team = self.env["mail.activity"]._get_default_team_id(
            user_id=self.user2.id, model_id=user_ir_model.id
        )
        self.assertFalse(
            result_team,
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
        result_team = self.env["mail.activity"]._get_default_team_id(
            user_id=self.user.id, model_id=self.partner_ir_model.id
        )
        self.assertEqual(
            result_team,
            team_b,
            "Should return the team with model match",
        )
        # Verify it's a single record
        self.assertEqual(len(result_team), 1, "Should return only one team")

    def test_create_activity_without_team_assigns_no_team(self):
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
        self.assertFalse(
            activity.team_id,
            "Team should not be assigned when team_user_id is used without team_id",
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
