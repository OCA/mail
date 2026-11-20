# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import itertools

from odoo import api, fields, models, tools


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    partner_cc_ids = fields.Many2many(
        "res.partner",
        "mail_compose_message_res_partner_cc_rel",
        "wizard_id",
        "partner_id",
        string="Cc",
        compute="_compute_partner_cc_bcc_ids",
        readonly=False,
        store=True,
    )
    partner_bcc_ids = fields.Many2many(
        "res.partner",
        "mail_compose_message_res_partner_bcc_rel",
        "wizard_id",
        "partner_id",
        string="Bcc",
        compute="_compute_partner_cc_bcc_ids",
        readonly=False,
        store=True,
    )

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    @api.depends(
        "composition_mode",
        "message_type",
        "model",
        "parent_id",
        "res_domain",
        "res_ids",
        "template_id",
    )
    def _compute_partner_cc_bcc_ids(self):
        """Fill Cc / Bcc from the template, the answered message or the
        company defaults."""
        for composer in self:
            # The company defaults are meant for emails a user writes: on
            # automatic ones (e.g. the order confirmation) every email would get them
            is_user_email = composer.message_type == "comment"
            company = self.env.company if is_user_email else self.env["res.company"]
            if composer._is_cc_bcc_template_composer():
                template = composer.template_id
                res_id = (composer._evaluate_res_ids() or [0])[0]
                # Rendered from the template fields themselves: with "Default
                # Recipients" (Odoo's order confirmation) Odoo ignores the
                # template Cc. Assigned, not added: switching template must not
                # keep the Cc of the previous one.
                emails_cc = template.email_cc and template._render_field(
                    "email_cc", [res_id]
                ).get(res_id)
                emails_bcc = template.email_bcc and template._render_field(
                    "email_bcc", [res_id]
                ).get(res_id)
                composer.partner_cc_ids = (
                    composer._get_partners_from_emails(emails_cc)
                    or company.default_partner_cc_ids
                )
                composer.partner_bcc_ids = (
                    composer._get_partners_from_emails(emails_bcc)
                    or company.default_partner_bcc_ids
                )
            elif not is_user_email:
                composer.partner_cc_ids = False
                composer.partner_bcc_ids = False
            elif composer.parent_id and composer.composition_mode == "comment":
                # A reply goes to the same Cc / Bcc as the message it answers
                composer.partner_cc_ids = composer.parent_id.recipient_cc_ids
                composer.partner_bcc_ids = composer.parent_id.recipient_bcc_ids
            elif not composer.template_id:
                composer.partner_cc_ids = company.default_partner_cc_ids
                composer.partner_bcc_ids = company.default_partner_bcc_ids

    @api.depends(
        "composition_mode", "model", "parent_id", "res_domain", "res_ids", "template_id"
    )
    def _compute_partner_ids(self):
        """Keep the template Cc out of To: the module shows it in the Cc field.

        Odoo turns the template Cc into regular recipients. Composers without a
        template keep Odoo's own computation.
        """
        cc_bcc_composers = self.filtered(lambda c: c._is_cc_bcc_template_composer())
        res = super(MailComposeMessage, self - cc_bcc_composers)._compute_partner_ids()
        for composer in cc_bcc_composers:
            # With "Default Recipients", a To already filled in is kept
            if composer.template_id.use_default_to and composer.partner_ids:
                continue
            res_ids = composer._evaluate_res_ids() or [0]
            rendered_values = composer._generate_template_for_composer(
                res_ids,
                {"email_to", "partner_ids"},
                find_or_create_partners=True,
            )[res_ids[0]]
            if rendered_values.get("partner_ids"):
                composer.partner_ids = rendered_values["partner_ids"]
        return res

    # ------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------

    def _is_cc_bcc_template_composer(self):
        """Whether a template fills the recipients: one record, comment mode."""
        self.ensure_one()
        return (
            self.template_id
            and self.composition_mode == "comment"
            and not self.composition_batch
        )

    def _get_partners_from_emails(self, emails):
        """Partners of the given emails, creating the unknown ones as Odoo does
        for the recipients of a template."""
        mails = tools.email_split(emails or "")
        if not mails:
            return self.env["res.partner"]
        partners = self.env["res.partner"]._find_or_create_from_emails(
            mails,
            additional_values={
                email: {"company_id": self.record_company_id.id}
                for email in itertools.chain(mails, [False])
            },
        )
        return self.env["res.partner"].union(*partners)

    # ------------------------------------------------------------
    # RENDERING / VALUES GENERATION
    # ------------------------------------------------------------

    def _prepare_mail_values_rendered(self, res_ids):
        """Store the Cc / Bcc on the message: every later step reads them there.

        Not the context: it would be lost when the email is sent later, and
        would leak to any other message posted in the same transaction.
        """
        mail_values = super()._prepare_mail_values_rendered(res_ids)
        # Mass mailing has no Cc / Bcc. A logged note must never be emailed:
        # its Cc / Bcc fields are hidden but may hold the company defaults.
        if self.composition_mode != "comment" or self.subtype_is_log:
            return mail_values
        for res_id in mail_values:
            mail_values[res_id].update(
                {
                    "recipient_cc_ids": self.partner_cc_ids.ids,
                    "recipient_bcc_ids": self.partner_bcc_ids.ids,
                }
            )
        return mail_values
