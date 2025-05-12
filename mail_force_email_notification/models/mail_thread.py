# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_get_recipients(self, message, msg_vals, **kwargs):
        recipients = super()._notify_get_recipients(message, msg_vals, **kwargs)
        # The context key `force_notification_by_email` allows to
        # push notifications through email even if the user has his preferences
        # configured to use Odoo.
        if self.env.context.get("force_notification_by_email"):
            for partner in recipients:
                partner["notif"] = "email"
        return recipients
