# Copyright 2024 Camptocamp SA
# Copyright 2024 CorporateHub
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class MailActivitySchedule(models.TransientModel):
    _inherit = "mail.activity.schedule"

    activity_team_user_id = fields.Many2one(
        string="Team user", related="activity_user_id", store=True, readonly=False
    )
    activity_team_id = fields.Many2one(
        "mail.activity.team",
        "Team assigned to",
        compute="_compute_activity_team_id",
        store=True,
        readonly=False,
    )

    @api.depends("res_model_id", "activity_user_id")
    def _compute_activity_team_id(self):
        """Assign team if no team yet or team is incompatible"""
        for wizard in self:
            if (
                not wizard.activity_team_id
                or wizard.activity_user_id
                and wizard.activity_user_id not in wizard.activity_team_id.member_ids
                or (
                    wizard.res_model_id
                    and wizard.activity_team_id.res_model_ids
                    and wizard.res_model_id not in wizard.activity_team_id.res_model_ids
                )
            ):
                # Reuse mail.activity default team logic
                activity = self.env["mail.activity"].new(
                    values={
                        "res_model_id": wizard.sudo().res_model_id.id,
                        "user_id": wizard.activity_user_id.id,
                    },
                )
                wizard.activity_team_id = activity._get_default_team_id()

    @api.onchange("activity_team_id")
    def _onchange_activity_team_id(self):
        if (
            self.activity_team_id
            and self.activity_team_user_id not in self.activity_team_id.member_ids
        ):
            if self.activity_team_id.user_id:
                new_user_id = self.activity_team_id.user_id
            elif len(self.activity_team_id.member_ids) == 1:
                new_user_id = self.activity_team_id.member_ids
            else:
                new_user_id = self.env["res.users"]
            self.activity_team_user_id = new_user_id
            self.activity_user_id = new_user_id

    @api.onchange("activity_type_id")
    def _onchange_activity_type_id(self):
        if self.activity_type_id.default_team_id:
            self.activity_team_id = self.activity_type_id.default_team_id
            members = self.activity_type_id.default_team_id.member_ids
            if self.activity_user_id not in members and members:
                self.activity_user_id = members[:1]

    def _action_schedule_activities(self):
        return self._get_applied_on_records().activity_schedule(
            activity_type_id=self.activity_type_id.id,
            automated=False,
            summary=self.summary,
            note=self.note,
            user_id=self.activity_team_user_id.id,
            team_user_id=self.activity_team_user_id.id,
            team_id=self.activity_team_id.id,
            date_deadline=self.date_deadline,
        )
