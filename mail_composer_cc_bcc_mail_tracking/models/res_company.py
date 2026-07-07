# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    chatter_recipients_default_display = fields.Selection(
        selection=[
            ("collapsed", "Single 'To' line"),
            ("expanded", "To / Cc / Bcc split"),
        ],
        string="Default recipient display",
        default="collapsed",
        required=True,
        help="How chatter recipients are shown by default: a single collapsed "
        "'To' line, or the full To/Cc/Bcc split.",
    )
    chatter_recipients_allow_toggle = fields.Boolean(
        string="Allow toggling chatter recipients",
        default=True,
        help="Let users switch between the single 'To' line and the full "
        "To/Cc/Bcc display. When disabled, only the default display is shown.",
    )
