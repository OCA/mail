# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    parse_all_html_documents_in_mail = fields.Boolean(
        string="Keep every HTML document of an incoming mail",
        default=True,
        help="Odoo keeps only the first HTML document of an incoming mail.",
    )
