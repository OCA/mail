# Copyright 2018-22 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import get_lang

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
                    lambda mat, model_id=model_id: model_id
                    in mat.sudo().res_model_ids.ids
                )
                or teams
            )
        return teams[:1]

    user_id = fields.Many2one(required=False, default=False)
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
        new_vals_list = []
        for vals in vals_list:
            new_vals = vals.copy()
            # we need to be sure that we are in a context where the team_id is set,
            # and we don't want to use user_id
            if new_vals.get("team_id"):
                # using team, we have user_id = team_user_id,
                # so if we don't have a user_team_id we don't want user_id too
                if "user_id" in new_vals and not new_vals.get("team_user_id"):
                    del new_vals["user_id"]
            # team_user_id is a related field pointing to user_id (readonly=False).
            # If left in vals, the ORM places it in the 'inversed' bucket and
            # calls _inverse_related *after* the initial INSERT while user_id is
            # still NULL. That triggers Model.write({'user_id': …}) which in turn
            # fires action_notify() → action_notify_team() a first time, and then
            # core mail.activity.create()'s post-hook fires action_notify() a
            # second time — causing duplicate notifications for team members.
            # Eagerly resolving team_user_id to user_id here ensures user_id is
            # stored in the INSERT so no inverse write occurs.
            if "team_user_id" in new_vals:
                team_user_id_val = new_vals.pop("team_user_id")
                new_vals.setdefault("user_id", team_user_id_val)
            new_vals_list.append(new_vals)
        activities = super().create(new_vals_list)
        if not self.env.context.get("mail_activity_quick_update"):
            # Core create() triggers action_notify() only for activities assigned to
            # users different from the current one. Notify team members here only for
            # activities not covered by that path to avoid duplicate notifications.
            activities_without_core_notify = activities.filtered(
                lambda activity: activity.user_id == self.env.user
            )
            activities_without_core_notify.action_notify_team()
        return activities

    def write(self, values):
        # Notify the new team, but prevent duplicate notifications by excluding
        # activities that will be notified by core write()->action_notify()
        # when the user changes.
        team_notify_activities = self.env["mail.activity"]
        core_notified_activities = self.env["mail.activity"]
        if not self.env.context.get("mail_activity_quick_update", False):
            new_team_id = values.get("team_id", False)
            team_notify_activities = self.filtered(
                lambda activity, new_team_id=new_team_id: new_team_id
                and activity.team_id.id != new_team_id
            )
            new_user_id = values.get("user_id", False)
            user_changed_activities = self.filtered(
                lambda activity, new_user_id=new_user_id: new_user_id
                and activity.user_id.id != new_user_id
            )
            team_notify_activities |= user_changed_activities

            # Core write() calls action_notify() for user changes except when
            # assigning to the current user; avoid re-sending team notifications.
            if new_user_id != self.env.uid:
                core_notified_activities = user_changed_activities

        res = super().write(values)
        # notify new responsibles

        if not self.env.context.get("mail_activity_quick_update", False):
            (team_notify_activities - core_notified_activities).action_notify_team()
        return res

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

    def _to_store_defaults(self, target):
        return [
            *super()._to_store_defaults(target),
            Store.One("team_id", "name"),
        ]

    @api.onchange("activity_type_id")
    def _onchange_activity_type_id(self):
        res = super()._onchange_activity_type_id()
        if self.activity_type_id.default_team_id:
            self.team_id = self.activity_type_id.default_team_id
            members = self.activity_type_id.default_team_id.member_ids
            if self.user_id not in members and members:
                self.user_id = members[:1]
        return res

    def action_notify_team(self):
        # Like action_notify(), but for team members.
        classified = self._classify_by_model()
        for model, activity_data in classified.items():
            records_sudo = self.env[model].sudo().browse(activity_data["record_ids"])
            # in case record was cascade-deleted in DB, skipping unlink override
            activity_data["record_ids"] = records_sudo.exists().ids

        for activity in self:
            if activity.res_id not in classified[activity.res_model]["record_ids"]:
                continue
            if not activity.team_id.notify_members:
                continue

            record = activity.env[activity.res_model].browse(activity.res_id)
            # Notify each team member except the assigned user and the current user
            members = activity.team_id.member_ids.filtered(
                lambda member, assigned_user_id=activity.user_id: self.env.uid
                not in member.user_ids.ids
                and (
                    not assigned_user_id
                    or (assigned_user_id and assigned_user_id not in member.user_ids)
                )
            )
            for member in members:
                activity_ctx = (
                    activity.with_context(lang=member.lang) if member.lang else activity
                )
                model_description = (
                    activity_ctx.env["ir.model"]
                    ._get(activity_ctx.res_model)
                    .display_name
                )
                body = activity_ctx.env["ir.qweb"]._render(
                    "mail.message_activity_assigned",
                    {
                        "activity": activity_ctx,
                        "model_description": model_description,
                        "is_html_empty": lambda value: not value
                        or value == "<p><br></p>",
                    },
                    minimal_qcontext=True,
                )
                record.message_notify(
                    partner_ids=member.sudo().partner_id.ids,
                    body=body,
                    model_description=model_description,
                    email_layout_xmlid="mail.mail_notification_layout",
                    subject=self.env._(
                        "%(activity_name)s: %(summary)s (Team Activity)",
                        activity_name=activity_ctx.res_name,
                        summary=activity_ctx.summary
                        or activity_ctx.activity_type_id.name,
                    ),
                    subtitles=[
                        self.env._("Activity: %s", activity_ctx.activity_type_id.name),
                        self.env._("Team: %s", activity_ctx.team_id.name),
                        self.env._(
                            "Deadline: %s",
                            (
                                activity_ctx.date_deadline.strftime(
                                    get_lang(activity_ctx.env).date_format
                                )
                                if hasattr(activity_ctx.date_deadline, "strftime")
                                else str(activity_ctx.date_deadline)
                            ),
                        ),
                    ],
                )

    def action_notify(self):
        """Override to notify team members when notify_members is enabled."""
        result = super().action_notify()
        self.action_notify_team()
        return result
