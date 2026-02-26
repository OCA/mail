from datetime import datetime

from odoo import api, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.model
    def get_sent_history(self, limit=30, before=None, after=None):
        partner = self.env.user.partner_id
        domain = [
            ("author_id", "=", partner.id),
            ("message_type", "in", ["comment"]),
        ]

        res = self._message_fetch(
            domain,
            before=before,
            after=after,
            limit=limit,
        )
        messages = res["messages"]._filter_existing_records()
        messages_formatted = messages.message_format()
        messages_sorted = sorted(
            messages_formatted,
            key=lambda m: m["date"] or datetime.min,
        )
        return {**res, "messages": messages_sorted}

    def _filter_existing_records(self):
        existing = self.browse()
        for message in self:
            if not message.model or not message.res_id:
                existing += message
            elif self.env[message.model].browse(message.res_id).exists():
                existing += message
        return existing
