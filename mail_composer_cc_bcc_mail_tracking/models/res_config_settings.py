# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    chatter_recipients_default_display = fields.Selection(
        related="company_id.chatter_recipients_default_display",
        readonly=False,
        required=True,
    )
    chatter_recipients_allow_toggle = fields.Boolean(
        related="company_id.chatter_recipients_allow_toggle",
        readonly=False,
    )
