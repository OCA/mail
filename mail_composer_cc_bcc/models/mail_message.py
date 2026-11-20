# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    recipient_cc_ids = fields.Many2many(
        "res.partner",
        "mail_message_res_partner_cc_rel",
        "mail_message_id",
        "parent_id",
        string="Cc (Partners)",
        context={"active_test": False},
    )
    recipient_bcc_ids = fields.Many2many(
        "res.partner",
        "mail_message_res_partner_bcc_rel",
        "mail_message_id",
        "parent_id",
        string="Bcc (Partners)",
        context={"active_test": False},
    )

    def _get_cc_bcc_audience(self):
        """Split the audience in visible To / Cc and hidden Bcc partners.

        The single place for this rule: the emails are created and sent from
        it, so both steps agree. A partner in To and in Cc / Bcc stays in To.
        """
        self.ensure_one()
        message = self.sudo()
        partners_to = message.partner_ids
        partners_cc = message.recipient_cc_ids - partners_to
        partners_bcc = message.recipient_bcc_ids - partners_to - partners_cc
        return partners_to, partners_cc, partners_bcc
