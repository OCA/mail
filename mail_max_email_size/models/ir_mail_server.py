# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright 2026 Quartile (https://www.quartile.co)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    max_email_size = fields.Float()

    def _get_max_email_size(self):
        if self.max_email_size:
            return self.max_email_size
        return float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("base.default_max_email_size", "10")
        )
