# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models, tools


def format_emails(partners):
    # Odoo only delivers a copy to addresses that match, case included, the
    # normalized address it computed: a raw "Bart@Iko.com" would block it
    return [
        tools.formataddr((p.name or "", email))
        for p in partners
        for email in tools.mail.email_normalize_all(p.email)
    ]


def format_emails_raw(partners):
    return [p.email for p in partners if p.email]


def format_emails_str(partners):
    emails = format_emails(partners)
    return ", ".join(emails)


class MailMail(models.Model):
    _inherit = "mail.mail"

    email_bcc = fields.Char("Bcc", help="Blind Cc message recipients")

    def _prepare_outgoing_list(
        self, mail_server=False, recipients_follower_status=None
    ):
        """Give every copy the same To and Cc headers, as a mail client does.

        Odoo sends one copy per recipient, each showing only that recipient.
        For a message with Cc / Bcc, every copy shows the To and Cc partners of
        the message instead, and the Bcc partners and followers stay hidden.
        """
        res = super()._prepare_outgoing_list(
            mail_server=mail_server,
            recipients_follower_status=recipients_follower_status,
        )
        # Only set on emails of a message with Cc / Bcc: checking them first
        # spares reading the message for every other email
        if not self.email_cc and not self.email_bcc:
            return res
        # From the message, not the context: the email is then built the same
        # way when sent right away, by the email queue or again with Retry
        partners_to, partners_cc, partners_bcc = (
            self.mail_message_id._get_cc_bcc_audience()
        )
        if not partners_cc and not partners_bcc:
            return res

        # Without To addresses, Odoo adds one copy for the Cc addresses only.
        # Every Cc partner already has a copy of its own: it would get two.
        res = [m for m in res if m["email_to"]]

        email_to = format_emails(partners_to)
        email_to_raw = format_emails_raw(partners_to)
        email_cc = format_emails(partners_cc)

        for m in res:
            # Odoo delivers a copy only to its own recipient, even when the
            # headers list everyone: that keeps every copy private. A copy
            # without a valid address has nobody to go to: leave it to Odoo,
            # which then marks only that recipient as failed.
            if not m["partner_id"] or not m["email_to_normalized"]:
                continue

            # Odoo shares one headers dict between all copies: without a copy,
            # one recipient's Bcc would land in everyone's email
            headers = dict(m["headers"])
            # Bcc partners and followers must not appear in To or Cc, but Odoo
            # only delivers to addresses found in the headers. A Bcc header
            # with their own address lets the copy reach them, and Odoo removes
            # Bcc before sending, so nobody sees it.
            if m["partner_id"] not in partners_to + partners_cc:
                headers["Bcc"] = ", ".join(m["email_to"])

            m.update(
                {
                    "email_to": email_to,
                    "email_to_raw": email_to_raw,
                    "email_cc": email_cc,
                    "headers": headers,
                }
            )

        return res
