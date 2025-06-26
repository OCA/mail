# Copyright 2025 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _message_add_suggested_recipient(
        self, result, partner=None, email=None, lang=None, reason=""
    ):
        # Uncheck all the suggested recipients updating the dictionary value
        res = super()._message_add_suggested_recipient(
            result, partner=partner, email=email, lang=lang, reason=reason
        )
        for item in res:
            item.update({"checked": False})
        return res
