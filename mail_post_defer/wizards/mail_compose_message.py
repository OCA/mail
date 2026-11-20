# Copyright 2025 Moduon Team S.L. <info@moduon.team>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import timedelta

from odoo import fields, models
from odoo.tools import config


class MailComposer(models.TransientModel):
    _inherit = "mail.compose.message"

    def _prepare_mail_values_rendered(self, res_ids):
        result = super()._prepare_mail_values_rendered(res_ids)
        # During tests, don't defer unless a test explicitly opts in
        if config["test_enable"] and not self.env.context.get("test_mail_post_defer"):
            return result
        for res_id in res_ids:
            if not result[res_id].get("scheduled_date"):
                result[res_id]["scheduled_date"] = fields.Datetime.now() + timedelta(
                    seconds=30
                )
        return result
