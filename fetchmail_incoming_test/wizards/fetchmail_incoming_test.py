# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from email.message import EmailMessage
from email.utils import make_msgid

from odoo import _, fields, models


class FetchmailIncomingTest(models.TransientModel):
    _name = "fetchmail.incoming.test"
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

    def action_process(self):
        """Feed the composed email to the mail gateway as a real inbound one."""
        self.ensure_one()
        thread_id = self.env["mail.thread"].message_process(
            None, self._build_raw_message()
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("Email processed"),
                "message": _("The gateway created record #%s.", thread_id),
                "sticky": False,
                # Close the wizard dialog once the notification is shown.
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
