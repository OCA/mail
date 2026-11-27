# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    disable_incoming_mail_forward = fields.Boolean(
        related="company_id.disable_incoming_mail_forward",
        readonly=False,
    )
    notify_internal_on_incoming_email = fields.Boolean(
        related="company_id.notify_internal_on_incoming_email",
        readonly=False,
    )
