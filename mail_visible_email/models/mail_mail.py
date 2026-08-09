# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, models, tools


def list_emails(partners):
    return [
        tools.mail.email_normalize(p.email)
        for p in partners
        if p.email and tools.mail.email_normalize(p.email)
    ]


class MailMail(models.Model):
    _inherit = "mail.mail"

    @api.model_create_multi
    def create(self, values_list):
        mails = super().create(values_list)
        for mail in mails:
            message_vals = {}
            email_values = mail._get_email_values()
            for fname in ("email_to", "email_cc", "email_bcc"):
                emails = email_values.get(fname, [])
                if emails:
                    message_vals[fname] = mail._append_email(fname, emails)
            if message_vals:
                mail.mail_message_id.write(message_vals)
        return mails

    def _get_email_values(self):
        """Return normalized email lists for to, cc and bcc.
        - Composer send: recipient_cc_ids/recipient_bcc_ids are set on mail.mail
          at create time by the composer's _prepare_mail_values.
        - Template send (send_mail): email_to, email_cc, email_bcc
          are written directly to mail.mail at create time from the rendered
          template values.
        """
        self.ensure_one()
        cc_bcc = self.recipient_cc_ids + self.recipient_bcc_ids
        to_partners = self.recipient_ids - cc_bcc
        return {
            "email_to": list_emails(to_partners)
            or tools.mail.email_normalize_all(self.email_to or ""),
            "email_cc": list_emails(self.recipient_cc_ids)
            or tools.mail.email_normalize_all(self.email_cc or ""),
            "email_bcc": list_emails(self.recipient_bcc_ids)
            or tools.mail.email_normalize_all(self.email_bcc or ""),
        }

    def _append_email(self, fieldname, emails):
        """Merge new emails with any already stored on mail.message."""
        self.ensure_one()
        existing = self.mail_message_id[fieldname]
        if existing:
            emails += existing.split(",")
        return ",".join(dict.fromkeys(filter(None, emails)))
