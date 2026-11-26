# Copyright 2026 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_get_recipients(self, message, msg_vals, **kwargs):
        recipients_data = super()._notify_get_recipients(message, msg_vals, **kwargs)
        email_recipients = [r for r in recipients_data if r["notif"] == "email"]
        if len(email_recipients) < 2:
            return recipients_data
        partners = (
            self.env["res.partner"].sudo().browse([r["id"] for r in email_recipients])
        )
        email_by_partner = {p.id: p.email_normalized for p in partners}
        if msg_vals and "partner_ids" in msg_vals:
            addressed_ids = set(msg_vals["partner_ids"])
        else:
            addressed_ids = set(message.sudo().partner_ids.ids)
        kept_by_email = {}
        for rdata in sorted(
            email_recipients,
            key=lambda r: (r["share"], r["id"] not in addressed_ids),
        ):
            email = email_by_partner[rdata["id"]]
            if email:
                kept_by_email.setdefault(email, rdata["id"])
        kept_ids = set(kept_by_email.values())
        return [
            r
            for r in recipients_data
            if r["notif"] != "email"
            or not email_by_partner[r["id"]]
            or r["id"] in kept_ids
        ]
