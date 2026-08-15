# Copyright 2026 Codeforward B.V. - Jord Duineveld
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_by_email_render_layout(
        self, message, recipients_group, msg_vals=False, render_values=None
    ):
        mail_body = super()._notify_by_email_render_layout(
            message, recipients_group, msg_vals=msg_vals, render_values=render_values
        )
        return self.env["mail.render.mixin"].remove_href_odoo(mail_body or "")
