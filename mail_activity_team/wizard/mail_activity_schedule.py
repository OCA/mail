# Copyright 2024 Camptocamp SA
# Copyright 2024 CorporateHub
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import inspect
import logging

from odoo import api, fields, models
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)


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

    @api.depends("activity_type_id")
    def _compute_activity_team_id(self):
        for scheduler in self:
            if scheduler.activity_type_id.default_team_id:
                scheduler.activity_team_id = scheduler.activity_type_id.default_team_id
            elif not scheduler.activity_team_id:
                scheduler.activity_team_id = self.env[
                    "mail.activity"
                ]._get_default_team_id(
                    scheduler.activity_team_user_id.id, scheduler.sudo().res_model_id.id
                )

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

    @api.onchange("activity_team_user_id")
    def _onchange_activity_team_user_id(self):
        if not self.activity_team_user_id or (
            self.activity_team_user_id
            and self.activity_team_user_id in self.activity_team_id.member_ids
        ):
            return
        self.activity_team_id = self.env["mail.activity"]._get_default_team_id(
            self.activity_team_user_id.id, self.sudo().res_model_id.id
        )

    def _action_schedule_activities(self):
        # Insert default team data which is picked up for activities that are
        # created without a team already.
        self = self.with_context(
            schedule_default_team_id=self.activity_team_id.id,
            schedule_default_team_user_id=self.activity_team_user_id.id,
            schedule_default_user_id=self.activity_team_user_id.id,
        )
        return super()._action_schedule_activities()

    def action_schedule_plan(self):
        # Triggering scheduled team activities in
        # _plan_filter_activity_templates_to_schedule which is called from the
        # super method to fetch the activities that need to be scheduled.
        # This is because activity parameters are determined inline in the
        # super method, and the activity team cannot be inserted there in a
        # clean override.
        self = self.with_context(fire_team_activities=True)
        return super().action_schedule_plan()

    @staticmethod
    def _get_activity_schedule_plan_data():
        """Fetch some variables defined in action_schedule_plan"""
        frame = inspect.currentframe()
        while frame.f_back:
            frame = frame.f_back
            f_locals = frame.f_locals
            if "activity_descriptions" in f_locals and "record" in f_locals:
                return f_locals["record"], f_locals["activity_descriptions"]
        _logger.warning(
            "Could not find 'activity_descriptions' list in inspected frames"
        )
        return None, None

    def _plan_filter_activity_templates_to_schedule(self):
        # Instead of returning all templates, including those with a team,
        # go ahead and schedule only those with a team and only return
        # the remaining activity templates.
        res = super()._plan_filter_activity_templates_to_schedule()
        if self.env.context.get("fire_team_activities"):
            # Immediately schedule team activities
            record, activity_descriptions = self._get_activity_schedule_plan_data()
            if record is None:
                return res
            templates = res.filtered("activity_team_required")
            others = res - templates
            for template in templates:
                date_deadline = template._get_date_deadline(self.plan_date)
                record.activity_schedule(
                    activity_type_id=template.activity_type_id.id,
                    automated=False,
                    summary=template.summary,
                    note=template.note,
                    user_id=template.activity_team_user_id.id,
                    team_id=template.activity_team_id.id,
                    date_deadline=date_deadline,
                )
                activity_descriptions.append(
                    self.env._(
                        "%(activity)s, assigned to team %(name)s, "
                        "due on the %(deadline)s",
                        activity=template.summary or template.activity_type_id.name,
                        name=template.activity_team_id.name,
                        deadline=format_date(self.env, date_deadline),
                    )
                )
            return others
        return res
