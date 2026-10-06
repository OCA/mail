# Copyright 2020 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict
from datetime import datetime, time

from dateutil.relativedelta import relativedelta
from pytz import UTC, timezone

from odoo import api, fields, models
from odoo.fields import Domain


class MailActivity(models.Model):
    _inherit = "mail.activity"

    next_reminder = fields.Datetime(
        string="Next reminder",
        compute="_compute_next_reminder",
        compute_sudo=True,
        store=True,
    )
    last_reminder_local = fields.Datetime(
        string="Last reminder (local)",
    )
    deadline = fields.Datetime(
        compute="_compute_deadline",
        compute_sudo=True,
        store=True,
    )
    reminder_level = fields.Integer(
        compute="_compute_reminder_level",
        compute_sudo=True,
        help="Number of reminders of the activity type already reached, "
        "0 when the deadline is not in the reminder timeframe yet.",
    )
    to_remind = fields.Boolean(
        compute="_compute_reminder_level",
        compute_sudo=True,
        search="_search_to_remind",
        help="The activity is not overdue but within the reminder timeframe "
        "of its activity type.",
    )

    @api.model
    def _get_activities_to_remind_domain(self):
        """Hook for extensions"""
        return [
            ("next_reminder", "<=", fields.Datetime.now()),
            ("deadline", ">=", fields.Datetime.now()),
        ]

    @api.model
    def _get_activities_to_remind(self):
        return self.search(self._get_activities_to_remind_domain())

    @api.model
    def _process_reminders(self):
        activities = self._get_activities_to_remind()
        activities.action_remind()
        return activities

    @api.model
    def _get_activities_to_report_domain(self):
        """Hook for extensions

        Candidate activities for the reminder report: every overdue activity
        and every activity whose deadline is close enough to be in the
        reminder timeframe of at least one activity type. The precise
        selection per user happens in ``_get_reminder_report_sections``.
        """
        offsets = [
            offset
            for activity_type in self.env["mail.activity.type"].search(
                [("reminders", "!=", False)]
            )
            for offset in activity_type._get_reminder_offsets()
        ]
        # One day of margin for users whose local date is ahead of UTC
        limit = fields.Date.today() + relativedelta(days=max(offsets, default=0) + 1)
        return [
            ("user_id", "!=", False),
            ("date_deadline", "<=", limit),
        ]

    @api.model
    def _get_activities_to_report(self):
        return self.search(self._get_activities_to_report_domain())

    @api.model
    def _process_reminder_report(self):
        activities = self._get_activities_to_report()
        return activities.action_send_reminder_report()

    @api.depends(
        "user_id.tz",
        "activity_type_id.reminders",
        "deadline",
        "last_reminder_local",
    )
    def _compute_next_reminder(self):
        now = fields.Datetime.now()
        for activity in self:
            if activity.deadline < now:
                activity.next_reminder = None
                continue
            reminders = activity.activity_type_id._get_reminder_offsets()
            if not reminders:
                activity.next_reminder = None
                continue
            reminders.sort(reverse=True)
            tz = timezone(activity.user_id.sudo().tz or "UTC")
            last_reminder_local = (
                tz.localize(activity.last_reminder_local)
                if activity.last_reminder_local
                else None
            )
            local_deadline = tz.localize(
                datetime.combine(
                    activity.date_deadline,
                    time.min,  # Schedule reminder based of beginning of day
                )
            )
            for reminder in reminders:
                next_reminder_local = local_deadline - relativedelta(
                    days=reminder,
                )
                if not last_reminder_local or next_reminder_local > last_reminder_local:
                    break
            if last_reminder_local and next_reminder_local <= last_reminder_local:
                activity.next_reminder = None
                continue
            activity.next_reminder = next_reminder_local.astimezone(UTC).replace(
                tzinfo=None
            )

    @api.depends("user_id.tz", "date_deadline")
    def _compute_deadline(self):
        for activity in self:
            tz = timezone(activity.user_id.sudo().tz or "UTC")
            activity.deadline = (
                tz.localize(datetime.combine(activity.date_deadline, time.max))
                .astimezone(UTC)
                .replace(tzinfo=None)
            )

    def action_notify(self):
        res = super().action_notify()
        utc_now = fields.Datetime.now().replace(tzinfo=UTC)
        for activity in self:
            if activity.last_reminder_local:
                continue
            tz = timezone(activity.user_id.sudo().tz or "UTC")
            activity.last_reminder_local = utc_now.astimezone(tz).replace(tzinfo=None)
        return res

    @api.depends(
        "active",
        "activity_type_id.reminders",
        "date_deadline",
        "user_id.tz",
    )
    def _compute_reminder_level(self):
        utc_now = fields.Datetime.now().replace(tzinfo=UTC)
        for activity in self:
            if not activity.date_deadline:
                activity.reminder_level = 0
                activity.to_remind = False
                continue
            tz = timezone(activity.user_id.sudo().tz or "UTC")
            today = utc_now.astimezone(tz).date()
            level = activity._get_reminder_level(today)
            activity.reminder_level = level
            activity.to_remind = bool(
                activity.active and level and activity.date_deadline >= today
            )

    def _search_to_remind(self, operator, value):
        if operator in ("=", "!="):
            values = {bool(value)}
        elif operator in ("in", "not in"):
            values = {bool(v) for v in value}
        else:
            return NotImplemented
        if operator in ("!=", "not in"):
            values = {True, False} - values
        if values == {True, False}:
            return Domain.TRUE
        if not values:
            return Domain.FALSE
        to_remind = self._get_activities_to_report().filtered("to_remind")
        return [("id", "in" if True in values else "not in", to_remind.ids)]

    def _get_reminder_level(self, today):
        """Return how many reminders of the activity type have been reached.

        :param today: local date of the assigned user
        :return: 0 when the deadline is not in the reminder timeframe yet,
            otherwise the 1-based level of the latest reached reminder: with
            reminders "5/2/0" and a deadline in 2 days the level is 2 (second
            reminder); the higher the level, the closer the deadline.
        """
        self.ensure_one()
        days_left = (self.date_deadline - today).days
        offsets = self.activity_type_id._get_reminder_offsets()
        return sum(1 for offset in offsets if offset >= days_left)

    def _get_reminder_report_sections(self, today):
        """Split activities into report sections ordered by criticality.

        Overdue activities come first, then the activities in the reminder
        timeframe grouped by reminder level, highest level first. Within a
        section activities are ordered by deadline. Activities that are not
        overdue and not in the reminder timeframe are left out.

        :param today: local date of the assigned user
        :return: list of dicts with keys ``title``, ``overdue``, ``level``
            and ``activities``
        """
        overdue = self.browse()
        by_level = defaultdict(self.browse)
        for activity in self:
            if activity.date_deadline < today:
                overdue |= activity
                continue
            level = activity._get_reminder_level(today)
            if level:
                by_level[level] |= activity
        sections = []
        if overdue:
            sections.append(
                {
                    "title": self.env._("Overdue"),
                    "overdue": True,
                    "level": 0,
                    "activities": overdue.sorted(lambda a: (a.date_deadline, a.id)),
                }
            )
        for level in sorted(by_level, reverse=True):
            sections.append(
                {
                    "title": self.env._("Reminder level %s", level),
                    "overdue": False,
                    "level": level,
                    "activities": by_level[level].sorted(
                        lambda a: (a.date_deadline, a.id)
                    ),
                }
            )
        return sections

    def action_send_reminder_report(self):
        """Send one report per user listing overdue and reminded activities.

        Unlike ``action_remind`` this does not touch ``last_reminder_local``:
        the report is an overview and not a reminder by itself.

        :return: the activities that were included in a report
        """
        MailThread = self.env["mail.thread"]
        utc_now = fields.Datetime.now().replace(tzinfo=UTC)
        by_user = defaultdict(self.browse)
        for activity in self:
            by_user[activity.user_id] |= activity
        reported = self.browse()
        for user, activities in by_user.items():
            activities = activities.with_context(lang=user.lang)
            today = utc_now.astimezone(timezone(user.sudo().tz or "UTC")).date()
            sections = activities._get_reminder_report_sections(today)
            if not sections:
                continue
            overdue = sum(
                len(section["activities"]) for section in sections if section["overdue"]
            )
            upcoming = sum(
                len(section["activities"])
                for section in sections
                if not section["overdue"]
            )
            subject = activities.env._(
                "Activity reminder report: %(overdue)s overdue, %(upcoming)s upcoming",
                overdue=overdue,
                upcoming=upcoming,
            )
            body = activities.env["ir.qweb"]._render(
                "mail_activity_reminder.message_activity_reminder_report",
                dict(
                    sections=sections,
                    today=today,
                    model_description="Activities",
                ),
                minimal_qcontext=True,
            )
            MailThread.message_notify(
                partner_ids=user.partner_id.ids,
                body=body,
                subject=subject,
                model_description="Activity",
                email_layout_xmlid="mail.mail_notification_light",
            )
            for section in sections:
                reported |= section["activities"]
        return reported

    def action_remind(self):
        """
        Group reminders by user and type and send them together
        """
        MailThread = self.env["mail.thread"]
        utc_now = fields.Datetime.now().replace(tzinfo=UTC)
        for user in self.mapped("user_id"):
            activities = self.filtered(
                lambda activity, user=user: activity.user_id == user
            )
            tz = timezone(user.sudo().tz or "UTC")
            local_now = utc_now.astimezone(tz)

            subject = self.env._("Some activities you are assigned to expire soon.")

            body = self.env["ir.qweb"]._render(
                "mail_activity_reminder.message_activity_assigned",
                dict(activities=activities, model_description="Activities"),
                minimal_qcontext=True,
            )
            MailThread.message_notify(
                partner_ids=user.partner_id.ids,
                body=body,
                subject=subject,
                model_description="Activity",
                notif_layout="mail.mail_notification_light",
            )
            activities.update({"last_reminder_local": local_now.replace(tzinfo=None)})
