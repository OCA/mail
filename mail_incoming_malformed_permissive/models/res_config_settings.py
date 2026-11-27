# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    parse_all_html_documents_in_mail = fields.Boolean(
        related="company_id.parse_all_html_documents_in_mail",
        readonly=False,
    )
