# Copyright 2023 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    activity_team_id = fields.Many2one("mail.activity.team")

    def _run_action_next_activity_multi(self, eval_context=None):
        # OVERRIDE to force the activity team on scheduled actions
        action = self
        if self.activity_user_type == "specific" and self.activity_team_id:
            action = self.with_context(force_activity_team=self.activity_team_id)
        return super(IrActionsServer, action)._run_action_next_activity_multi(
            eval_context=eval_context
        )

    @api.onchange("activity_team_id")
    def onchange_activity_team_id(self):
        if self.activity_team_id.user_id:
            self.activity_user_id = self.activity_team_id.user_id
