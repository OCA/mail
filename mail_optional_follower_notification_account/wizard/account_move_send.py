# Copyright 2024 NSI-SA (<http://nsi-sa.be>)
# Copyright 2025 Noviat - Jérémy Didderen
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMoveSend(models.TransientModel):
    _inherit = "account.move.send.wizard"

    notify_followers = fields.Boolean(default=True)

    @api.model
    def _send_mail(self, move, mail_template, **kwargs):
        if self.env.context.get("notify_followers"):
            kwargs["notify_followers"] = self.env.context.get("notify_followers")
            return super()._send_mail(move, mail_template, **kwargs)
        return super()._send_mail(move, mail_template, **kwargs)

    def action_send_and_print(self, allow_fallback_pdf=False):
        self.ensure_one()
        return super(
            AccountMoveSend, self.with_context(notify_followers=self.notify_followers)
        ).action_send_and_print(allow_fallback_pdf)
