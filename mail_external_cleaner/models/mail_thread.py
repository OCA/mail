# Copyright 2025 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_get_recipients_groups(self, msg_vals=None):
        """
        Override to disable portal customer button access in email notifications.
        """
        groups = super()._notify_get_recipients_groups(msg_vals=msg_vals)
        for group, _group_func, group_vals in groups:
            if group == "portal_customer":
                group_vals["has_button_access"] = False
        return groups
