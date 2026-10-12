# Copyright 2018-22 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.mail.tools.discuss import Store


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _get_default_team_id(self, user_id=None, model_id=None):
        if not user_id:
            user_id = self.user_id.id or self.env.user.id
        if not model_id:
            model_id = self.res_model_id.id if self.res_model_id else None
        domain = []
        domain.append(("member_ids", "=", user_id))
        if model_id:
            domain += [
                "|",
                ("res_model_ids", "=", False),
                ("res_model_ids", "=", model_id),
            ]
        if not domain:
            return self.env["mail.activity.team"]
        teams = self.env["mail.activity.team"].search(domain)
        if model_id:
            # Prefer teams with a matching model
            teams = (
                teams.filtered(
                    lambda mat, model_id=model_id: (
                        model_id in mat.sudo().res_model_ids.ids
                    )
                )
                or teams
            )
        return teams[:1]

    team_user_id = fields.Many2one(
        string="Team user", related="user_id", readonly=False
    )

    team_id = fields.Many2one(
        comodel_name="mail.activity.team",
        index=True,
        compute="_compute_team_id",
        store=True,
        readonly=False,
    )

    @api.depends("activity_type_id")
    def _compute_user_id(self):
        # Team activities may stay unassigned (the whole team is responsible):
        # skip the core fallback to the current user for them.
        team_activities = self.filtered(
            lambda act: act.team_id and not act.user_id and not act.role_id
        )
        res = super(MailActivity, self - team_activities)._compute_user_id()
        for activity in team_activities:
            activity_type = activity.activity_type_id
            if activity_type.default_user_id or activity_type.default_role_id:
                activity.user_id = activity_type.default_user_id
        return res

    @api.depends("res_model_id", "user_id")
    def _compute_team_id(self):
        """Assign team if no team yet or team is incompatible"""
        for activity in self:
            if (
                not activity.team_id
                or activity.user_id
                and activity.user_id not in activity.team_id.member_ids
                or (
                    activity.res_model_id
                    and activity.team_id.res_model_ids
                    and activity.res_model_id not in activity.team_id.res_model_ids
                )
            ):
                activity.team_id = activity._get_default_team_id(
                    activity.user_id.id, activity.res_model_id.id
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
            # using team, we have user_id = team_user_id,
            # so if we don't have a user_team_id we don't want user_id too
            if (
                vals.get("team_id")
                and "user_id" in vals
                and not vals.get("team_user_id")
            ):
                del vals["user_id"]
        return super().create(vals_list)

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
                    self.env._(
                        "The assigned user %(user_name)s is "
                        "not member of the team %(team_name)s.",
                        user_name=activity.user_id.name,
                        team_name=activity.team_id.name,
                    )
                )

    def _store_activity_fields(self, res: Store.FieldList):
        res.one("team_id", ["name"])
        return super()._store_activity_fields(res)

    @api.onchange("activity_type_id")
    def _onchange_activity_type_id(self):
        if self.activity_type_id.default_team_id:
            self.team_id = self.activity_type_id.default_team_id
            members = self.activity_type_id.default_team_id.member_ids
            if self.user_id not in members and members:
                self.user_id = members[:1]
