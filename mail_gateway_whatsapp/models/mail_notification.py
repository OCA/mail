# Copyright 2026 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

# WhatsApp delivery statuses, from the least to the most advanced one.
WHATSAPP_STATUSES = ["sent", "delivered", "read"]


class MailNotification(models.Model):
    _inherit = "mail.notification"

    whatsapp_status = fields.Selection(
        selection=[("sent", "Sent"), ("delivered", "Delivered"), ("read", "Read")],
        readonly=True,
        help="Last delivery status reported by WhatsApp for this message.",
    )

    def _to_store_defaults(self, target):
        return super()._to_store_defaults(target) + ["whatsapp_status"]

    def _set_whatsapp_status(self, status):
        """Store the status only when it is more advanced than the current one,
        as WhatsApp doesn't guarantee the order of the status webhooks."""
        rank = WHATSAPP_STATUSES.index(status)
        to_update = self.filtered(
            lambda n: n.notification_status == "sent"
            and (
                not n.whatsapp_status
                or WHATSAPP_STATUSES.index(n.whatsapp_status) < rank
            )
        )
        to_update.write({"whatsapp_status": status})
        return to_update
