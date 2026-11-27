# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    disable_incoming_mail_forward = fields.Boolean(
        string="Don't forward incoming mails to followers",
        default=True,
        help="Odoo forwards incoming mails to all the followers by email.",
    )
    notify_internal_on_incoming_email = fields.Boolean(
        string="Email internal users about incoming mails",
        default=True,
        help="Forward incoming mails to internal followers notified by email.",
    )
