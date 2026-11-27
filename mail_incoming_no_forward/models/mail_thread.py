# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_get_recipients(self, message, msg_vals, **kwargs):
        recipients = super()._notify_get_recipients(message, msg_vals, **kwargs)
        message_type = (
            msg_vals.get("message_type") if msg_vals else message.sudo().message_type
        )
        if message_type == "email" and self.env.company.disable_incoming_mail_forward:
            recipients = self._filter_forward_recipients(recipients)
        return recipients

    def _filter_forward_recipients(self, recipients):
        """Don't forward incoming mails to external followers.

        The forward leaks replies meant for the company only
        and is flagged as impersonation by some mail servers.

        Senders must decide who receives the message (e.g. "Reply all").
        """
        notify_internal = self.env.company.notify_internal_on_incoming_email
        return [
            recipient
            for recipient in recipients
            if recipient["notif"] != "email"
            or (notify_internal and not recipient["share"])
        ]
