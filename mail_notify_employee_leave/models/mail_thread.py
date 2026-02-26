from datetime import timedelta

from odoo import _, fields, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        recipients_data = super()._notify_thread(message, msg_vals=msg_vals, **kwargs)
        if self.env.context.get("skip_absence_notification"):
            return recipients_data

        affected_partner_ids = message.partner_ids.ids

        today = fields.Date.today()

        for partner_id in affected_partner_ids:
            partner = self.env["res.partner"].browse(partner_id)
            employee = self.env["hr.employee"].search(
                [("user_id.partner_id", "=", partner.id)], limit=1
            )
            if employee and employee.is_absent:
                if employee.absence_notified_date != today:
                    employee.absence_notified_user_ids = [(5, 0, 0)]
                    employee.absence_notified_date = today

                if self.env.user not in employee.absence_notified_user_ids:
                    leave_date = fields.Date.from_string(employee.leave_date_to)
                    back_date = self.add_working_day(leave_date, employee)
                    body = _(
                        "%(name)s is out of office, expected back on %(date)s."
                    ) % {
                        "name": employee.name,
                        "date": fields.Date.to_string(back_date),
                    }
                    self.message_notify(
                        partner_ids=[self.env.user.partner_id.id],
                        body=body,
                        subject=_("User out of office"),
                        subtype_xmlid="mail.mt_note",
                        notify_author=True,
                    )
                    employee.absence_notified_user_ids = [(4, self.env.user.id)]

        return recipients_data

    def add_working_day(self, date_obj, employee):
        """
        Returns the next working day after `date_obj` considering
        the employee's calendar.
        """
        if not employee.resource_calendar_id:
            return date_obj + timedelta(days=1)

        calendar = employee.resource_calendar_id
        working_days = set(int(a.dayofweek) for a in calendar.attendance_ids)
        next_day = date_obj + timedelta(days=1)

        while True:
            if not working_days:
                break

            if next_day.weekday() not in working_days:
                next_day += timedelta(days=1)
                continue

            holiday = self.env["resource.calendar.leaves"].search(
                [
                    ("calendar_id", "in", [calendar.id, False]),
                    ("resource_id", "=", False),
                    ("date_from", "<=", next_day),
                    ("date_to", ">=", next_day),
                ],
                limit=1,
            )

            if holiday:
                next_day += timedelta(days=1)
                continue

            break

        return next_day
