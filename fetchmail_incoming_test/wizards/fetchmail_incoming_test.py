# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from email.message import EmailMessage
from email.utils import make_msgid

from odoo import fields, models


class FetchmailIncomingTest(models.TransientModel):
    _name = "fetchmail.incoming.test"
    _inherit = "fetchmail.incoming.test.mixin"
    _description = "Simulate an Incoming Email"

    email_from = fields.Char(
        string="From",
        required=True,
        default=lambda self: self.env.user.email_formatted,
    )
    email_to = fields.Char(
        string="To",
        required=True,
        help="Recipient address, typically the alias routing to the target model.",
    )
    email_cc = fields.Char(string="Cc")
    email_bcc = fields.Char(string="Bcc")
    subject = fields.Char()
    body = fields.Html()

    def _build_raw_message(self):
        """Return the incoming email as raw bytes, as a mail server would."""
        self.ensure_one()
        message = EmailMessage()
        message["From"] = self.email_from
        message["To"] = self.email_to
        if self.email_cc:
            message["Cc"] = self.email_cc
        if self.email_bcc:
            message["Bcc"] = self.email_bcc
        message["Subject"] = self.subject or ""
        message["Message-Id"] = make_msgid()
        message.set_content(self.body or "", subtype="html")
        return message.as_bytes()
