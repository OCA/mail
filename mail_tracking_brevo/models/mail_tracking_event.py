# Copyright 2026 CIT-Services
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailTrackingEvent(models.Model):
    _inherit = "mail.tracking.event"

    brevo_id = fields.Char(string="Brevo Event ID", index=True, copy=False)

    _sql_constraints = [
        ("brevo_id_unique", "UNIQUE(brevo_id)", "Brevo event IDs must be unique!")
    ]

    def _process_data(self, tracking_email, metadata, event_type, state):
        res = super()._process_data(tracking_email, metadata, event_type, state)
        res.update({"brevo_id": metadata.get("brevo_id", False)})
        return res
