# Copyright 2018-22 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    activity_team_ids = fields.Many2many(
        comodel_name="mail.activity.team",
        relation="mail_activity_team_users_rel",
        string="Activity Teams",
    )

    @api.model
    def _get_activity_groups(self):
        if not self.env.context.get("team_activities"):
            return super()._get_activity_groups()
        search_limit = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_int("mail.activity.systray.limit")
            or 1000
        )
        activities = self.env["mail.activity"].search(
            [("team_id", "in", self.env.user.activity_team_ids.ids)],
            order="id desc",
            limit=search_limit,
        )
        return self._divide_activities_in_groups(activities)

    def _format_activity_group(self, model_name, activities):
        res = super()._format_activity_group(model_name, activities)
        if self.env.context.get("team_activities"):
            # Team activities assigned to the current user are already counted
            # in "My Activities": only count the ones assigned to other members
            # (or to nobody) in the systray badge.
            res["total_count"] = len(
                activities.filtered(
                    lambda act: (
                        act.state in ("today", "overdue")
                        and act.user_id.id != self.env.uid
                    )
                )
            )
        return res
