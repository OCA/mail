# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


import os

from odoo import fields, models, tools

from odoo.addons.base.models.ir_mail_server import extract_rfc2822_addresses


def format_emails(partners):
    return [tools.formataddr((p.name or "", p.email)) for p in partners if p.email]


def format_emails_raw(partners):
    return [p.email for p in partners if p.email]


def format_emails_str(partners):
    emails = format_emails(partners)
    return ", ".join(emails)


class MailMail(models.Model):
    _inherit = "mail.mail"

    email_bcc = fields.Char("Bcc", help="Blind Cc message recipients")

    def _expose_bcc_marker(self):
        """Whether to also add the informational ``X-Odoo-Bcc`` marker header.

        Disabled by default: the marker survives sending and would expose the
        bcc recipient on every copy. Enable it through the ``expose_x_odoo_bcc``
        context key or the ``EXPOSE_X_ODOO_BCC`` environment variable.
        """
        if self.env.context.get("expose_x_odoo_bcc"):
            return True
        return tools.str2bool(os.environ.get("EXPOSE_X_ODOO_BCC") or "", False)

    def _prepare_outgoing_list(
        self, mail_server=False, recipients_follower_status=None
    ):
        # First, return if we're not coming from the Mail Composer
        res = super()._prepare_outgoing_list(
            mail_server=mail_server,
            recipients_follower_status=recipients_follower_status,
        )
        is_from_composer = self.env.context.get("is_from_composer", False)

        if not is_from_composer:
            return res

        # Every Cc partner is also a recipient and gets its own email,
        # so Odoo's Cc-only email is always a duplicate here.
        res = [m for m in res if m["email_to"]]

        # The To, Cc headers must be the same on every email, but no record
        # holds the whole audience: partner_ids is empty for followers, and the
        # mail.mail of the other langs are unlinked as they are sent.
        partners_cc_bcc = self.recipient_cc_ids + self.recipient_bcc_ids
        all_recipients = self.env["res.partner"].browse(
            self.env.context.get("composer_recipient_ids") or []
        )
        partner_to = all_recipients - partners_cc_bcc
        email_to = format_emails(partner_to)
        email_to_raw = format_emails_raw(partner_to)
        email_cc = format_emails_str(self.recipient_cc_ids)
        email_bcc = [r.email for r in self.recipient_bcc_ids if r.email]

        # Collect recipients (RCPT TO) and update all emails
        # with the same To, Cc headers (to be shown by email client as users expect)
        recipients = []
        for m in res:
            m_email_to = m["email_to"][0]
            rcpt_to = extract_rfc2822_addresses(m_email_to)[0]
            recipients.append(rcpt_to)

            # If the recipient is a Bcc, set a real Bcc header.
            # _prepare_email_message uses it to build the envelope
            # and then strips it, so it never leaks.
            if rcpt_to in email_bcc:
                # Avoid mutating the shared headers by making a copy
                m["headers"] = {**m["headers"], "Bcc": m_email_to}
                # Optional legacy marker. Unlike Bcc it survives sending,
                # so only add it when explicitly enabled (it would expose
                # the bcc recipient otherwise).
                if self._expose_bcc_marker():
                    m["headers"]["X-Odoo-Bcc"] = m_email_to

            m.update(
                {
                    "email_to": email_to,
                    "email_to_raw": email_to_raw,
                    "email_cc": email_cc,
                }
            )

        # Propagate recipients to override smtp_to `_prepare_email_message`
        self.env.context = {**self.env.context, "recipients": list(recipients)}

        return res
