from odoo import models


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _filter_existing_records(self):
        existing = self.browse()
        for message in self:
            if not message.model or not message.res_id:
                existing += message
            elif self.env[message.model].browse(message.res_id).exists():
                existing += message
        return existing
