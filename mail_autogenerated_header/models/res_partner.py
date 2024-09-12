# Copyright 2022 Hunki Enterprises BV <https://hunki-enterprises.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _notify(
        self,
        message,
        rdata,
        record,
        force_send=False,
        send_after_commit=True,
        model_description=False,
        mail_auto_delete=True,
    ):
        """Inhibit notifications if this is the notification for an incoming
        autogenerated mail from another system"""
        if self.env.context.get("mail_autogenerated_header"):
            return True
        return super()._notify(
            message,
            rdata,
            record,
            force_send=force_send,
            send_after_commit=send_after_commit,
            model_description=model_description,
            mail_auto_delete=mail_auto_delete,
        )
