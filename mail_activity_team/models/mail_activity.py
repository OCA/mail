# Copyright 2018-22 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import ValidationError


class MailActivity(models.Model):
    _inherit = "mail.activity"

    @api.model
    def _get_default_team_id(self, user_id=None, model_id=None):
        if not user_id:
            user_id = self.env.uid
        if not model_id:
            res_model = self.env.context.get("default_res_model")
            model = (
                self.sudo().env["ir.model"].search([("model", "=", res_model)], limit=1)
            )
            model_id = model.id if model else None
        domain = [("member_ids", "in", [user_id])]
        if model_id:
            domain.extend(
                [
                    "|",
                    ("res_model_ids", "=", False),
                    ("res_model_ids", "in", [model_id]),
                ]
            )
        results = self.env["mail.activity.team"].search(domain)
        if model_id:
            result_with_model = results.filtered(
                lambda team: model_id in team.res_model_ids.ids
            )
            if result_with_model:
                return result_with_model[0]

        return results[0] if results else self.env["mail.activity.team"]

    user_id = fields.Many2one(string="User", required=False, default=False)
    team_user_id = fields.Many2one(
        string="Team user", related="user_id", readonly=False
    )

    team_id = fields.Many2one(
        comodel_name="mail.activity.team",
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        # Differently from the previous odoo version,
        # the create method is called from (mail.activity.mixin).activity_schedule()
        # and on this method we are forcing the user_id to be the current user from
        # odoo import api, fields, models the default one linked to the activity type.
        # We don't want this behavior because using the team_id, we want to assign the
        # activity to the whole team.
        for vals in vals_list:
            # we need to be sure that we are in a context where the team_id is set,
            # and we don't want to use user_id
            if vals.get("team_id"):
                # using team, we have user_id = team_user_id,
                # so if we don't have a user_team_id we don't want user_id too
                if "user_id" in vals and not vals.get("team_user_id"):
                    del vals["user_id"]
            elif (
                "team_id" not in vals
                and "user_id" in vals
                and "team_user_id" not in vals
            ):
                # legacy behavior, if we have user_id but no team_id, set the team_id
                team_id = self._get_default_team_id(
                    vals["user_id"], vals.get("res_model_id")
                )
                if team_id:
                    vals["team_id"] = team_id.id
                    vals["team_user_id"] = vals["user_id"]
        return super().create(vals_list)

    @api.onchange("user_id")
    def _onchange_user_id(self):
        if not self.user_id or (
            self.team_id and self.user_id in self.team_id.member_ids
        ):
            return
        self.team_id = self._get_default_team_id(
            self.user_id.id, self.sudo().res_model_id.id
        )

    @api.onchange("team_id")
    def _onchange_team_id(self):
        if self.team_id and self.user_id not in self.team_id.member_ids:
            if self.team_id.user_id:
                self.user_id = self.team_id.user_id
            elif len(self.team_id.member_ids) == 1:
                self.user_id = self.team_id.member_ids
            else:
                self.user_id = self.env["res.users"]

    @api.constrains("team_id", "user_id")
    def _check_team_and_user(self):
        for activity in self:
            # SUPERUSER is used to put mail.activity on some objects
            # like sale.order coming from stock.picking
            # (for example with exception type activity, with no backorder).
            # SUPERUSER is inactive and then even if you add it
            # to member_ids it's not taken account
            # To not be blocked we must add it to constraint condition.
            # We must consider also users that could be archived but come from
            # an automatic scheduled activity
            if (
                activity.user_id.id != SUPERUSER_ID
                and activity.team_id
                and activity.user_id
                and activity.user_id
                not in activity.team_id.with_context(active_test=False).member_ids
            ):
                raise ValidationError(
                    _(
                        "The assigned user %(user_name)s is "
                        "not member of the team %(team_name)s.",
                        user_name=activity.user_id.name,
                        team_name=activity.team_id.name,
                    )
                )

    @api.onchange("activity_type_id")
    def _onchange_activity_type_id(self):
        res = super()._onchange_activity_type_id()
        if self.activity_type_id.default_team_id:
            self.team_id = self.activity_type_id.default_team_id
            members = self.activity_type_id.default_team_id.member_ids
            if self.user_id not in members and members:
                self.user_id = members[:1]
        return res
