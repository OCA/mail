# Copyright 2022-2024 Moduon Team S.L. <info@moduon.team>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import timedelta

from odoo import fields, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        """Defer emails by default."""
        # Don't defer automatically if forcing send
        _self = self
        if "mail_defer_seconds" not in _self.env.context:
            force_send = _self.env.context.get("mail_notify_force_send") or kwargs.get(
                "force_send", False
            )
            kwargs.setdefault("force_send", force_send)
            if not force_send:
                # If deferring message, give the user some minimal time to revert it
                _self = _self.with_context(mail_defer_seconds=30)
        # Apply deferring
        defer_seconds = _self.env.context.get("mail_defer_seconds")
        if defer_seconds:
            kwargs.setdefault(
                "scheduled_date",
                fields.Datetime.now() + timedelta(seconds=defer_seconds),
            )
        return super(MailThread, _self)._notify_thread(
            message, msg_vals=msg_vals, **kwargs
        )

    def _message_update_content(self, message, /, *, body, **kwargs):
        # If anything already went out, fall back to the standard behavior
        if any(ntf.notification_status == "sent" for ntf in message.notification_ids):
            return super()._message_update_content(message, body=body, **kwargs)
        scheduled_date = fields.Datetime.now() + timedelta(seconds=30)
        Schedule = self.env["mail.message.schedule"].sudo()
        sched = Schedule.search([("mail_message_id", "=", message.id)], limit=1)
        if sched:
            sched.scheduled_datetime = scheduled_date
        # In case emails are already created but not sent yet, cancel queued mails and
        # delete the notification (so nothing goes out with old content)
        else:
            message.mail_ids.filtered(
                lambda x: x.state in {"outgoing", "exception", "draft"}
            ).write({"state": "cancel"})
            message.notification_ids.filtered(
                lambda x: x.notification_status
                in {"ready", "exception", "canceled", "bounce"}
            ).unlink()
            Schedule.create(
                {"mail_message_id": message.id, "scheduled_datetime": scheduled_date}
            )
        kw = dict(kwargs)
        # Drop empty [] for partner_ids, or else Odoo will try to send to nobody
        if not kw.get("partner_ids"):
            kw.pop("partner_ids", None)
        res = super()._message_update_content(message, body=body, **kw)
        # Delete empty pending outgoing mails
        if empty_messages := message.sudo()._filter_empty():
            empty_messages.mail_ids.filtered(
                lambda mail: mail.state == "outgoing"
            ).unlink()
            empty_messages.env["mail.message.schedule"].search(
                [("mail_message_id", "in", empty_messages.ids)]
            ).unlink()
        return res
