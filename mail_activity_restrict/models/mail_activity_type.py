"""Extension to mail.activity.type model for write restriction."""

from odoo import fields, models


class MailActivityType(models.Model):
    """Extend mail.activity.type with write restriction control."""

    _inherit = "mail.activity.type"

    can_write_restrict = fields.Boolean(
        string="Restrict Write to Assigned User",
        default=False,
        help=(
            "If checked, only the assigned user (user_id field) can write/edit "
            "activities of this type. Other users cannot modify restricted activities."
        ),
    )
