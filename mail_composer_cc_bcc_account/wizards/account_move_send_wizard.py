# Copyright 2024 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
#
from odoo import Command, api, fields, models
from odoo.tools.mail import email_split


class AccountMoveSendWizard(models.TransientModel):
    _inherit = "account.move.send.wizard"

    partner_cc_ids = fields.Many2many(
        "res.partner",
        "account_move_send_wizard_res_partner_cc_rel",
        "wizard_id",
        "partner_id",
        string="Cc",
        compute="_compute_mail_partner_cc_bcc_ids",
        store=True,
        readonly=False,
    )
    partner_bcc_ids = fields.Many2many(
        "res.partner",
        "account_move_send_wizard_res_partner_bcc_rel",
        "wizard_id",
        "partner_id",
        string="Bcc",
        compute="_compute_mail_partner_cc_bcc_ids",
        store=True,
        readonly=False,
    )

    # -------------------------------------------------------------------------
    # DEFAULTS
    # -------------------------------------------------------------------------

    @api.model
    def default_get(self, fields_list):
        # EXTENDS 'base'
        results = super().default_get(fields_list)
        company = self.env.company
        partner_cc = company.default_partner_cc_ids
        if partner_cc:
            results["partner_cc_ids"] = [Command.set(partner_cc.ids)]
        partner_bcc = company.default_partner_bcc_ids
        if partner_bcc:
            results["partner_bcc_ids"] = [Command.set(partner_bcc.ids)]
        return results

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    def _get_partner_ids_from_mail(self, move, emails):
        partners = self.env["res.partner"].with_company(move.company_id)
        for mail_data in email_split(emails):
            partners |= partners.find_or_create(mail_data)
        return partners

    @api.depends("mail_template_id")
    def _compute_mail_partner_cc_bcc_ids(self):
        for wizard in self:
            if wizard.mail_template_id:
                wizard.partner_cc_ids = self._get_partner_ids_from_mail(
                    wizard.move_id, wizard.mail_template_id.email_cc
                )
                wizard.partner_bcc_ids = self._get_partner_ids_from_mail(
                    wizard.move_id, wizard.mail_template_id.email_bcc
                )
            else:
                wizard.partner_cc_ids = wizard.partner_bcc_ids = None

    @api.model
    def _send_mail(self, move, mail_template, **kwargs):
        move_with_context = move.with_context(
            is_from_composer=True,
            partner_cc_ids=self.partner_cc_ids,
            partner_bcc_ids=self.partner_bcc_ids,
        )
        return super()._send_mail(move_with_context, mail_template, **kwargs)
