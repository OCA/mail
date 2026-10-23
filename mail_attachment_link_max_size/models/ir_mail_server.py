# Copyright 2026 Quartile (https://www.quartile.co)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    max_email_size = fields.Float(
        help="Emails larger than this size (in MB) are sent with their attachments "
        "replaced by download links. When empty, the value of the system parameter "
        "'base.default_max_email_size' is used (10 MB if not set).",
    )

    def _get_max_email_size(self):
        if self.max_email_size:
            return self.max_email_size
        return float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("base.default_max_email_size", "10")
        )
