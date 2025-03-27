# Copyright 2025 Noviat - Jérémy Didderen
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.returns("mail.message", lambda value: value.id)
    def message_post(self, **kwargs):
        if "notify_followers" in kwargs:
            self = self.with_context(notify_followers=kwargs.get("notify_followers"))
            kwargs.pop("notify_followers")
        return super().message_post(**kwargs)
