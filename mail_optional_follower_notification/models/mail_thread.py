# Copyright 2019 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_get_recipients(self, message, **kwargs):
        """Compute recipients to notify based on subtype and followers. This
        method returns data structured as expected for ``_notify_recipients``."""
        if "notify_followers" in self.env.context and not self.env.context.get(
            "notify_followers", False
        ):
            kwargs["notify_skip_followers"] = True
        return super()._notify_get_recipients(message, **kwargs)
