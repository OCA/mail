# Copyright 2025 Aulora AG
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_thread_by_email(
        self, message, recipients_data, msg_vals=False, **kwargs
    ):
        """
        Remove recipients_data to prevent email generation when
        `mail_reply_stop_notification` is enabled.
        """
        if self.env.company.mail_reply_stop_notification:
            recipients_data = []
        return super()._notify_thread_by_email(
            message, recipients_data=recipients_data, msg_vals=msg_vals, **kwargs
        )
