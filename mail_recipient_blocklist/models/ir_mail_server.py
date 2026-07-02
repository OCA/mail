# Copyright 2026 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import api, models, tools
from odoo.tools import formataddr

_logger = logging.getLogger(__name__)


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    @api.model
    def _filter_blocked_recipient_header(self, header_value):
        allowed = []
        blocked = []
        BlockRule = self.env["mail.recipient.block.rule"]
        for name, email in tools.mail.email_split_tuples(str(header_value or "")):
            recipient = formataddr((name, email))
            if BlockRule._is_blocked_email(email):
                blocked.append(recipient)
            else:
                allowed.append(recipient)
        return ", ".join(allowed), blocked

    @api.model
    def _filter_blocked_message_recipients(self, message):
        blocked_recipients = []
        for header in ("To", "Cc", "Bcc"):
            header_value = message[header]
            if not header_value:
                continue
            allowed_header_value, blocked = self._filter_blocked_recipient_header(
                header_value
            )
            if not blocked:
                continue
            del message[header]
            if allowed_header_value:
                message[header] = allowed_header_value
            blocked_recipients += blocked
        if blocked_recipients:
            _logger.info(
                "Blocked SMTP recipient(s): %s",
                ", ".join(blocked_recipients),
            )
        has_remaining_recipients = bool(
            message["To"] or message["Cc"] or message["Bcc"]
        )
        return has_remaining_recipients, blocked_recipients

    def send_email(self, message, *args, **kwargs):
        has_remaining_recipients, blocked_recipients = (
            self._filter_blocked_message_recipients(message)
        )
        if blocked_recipients and not has_remaining_recipients:
            _logger.info(
                "Cancelled direct SMTP delivery addressed only to blocked "
                "recipients. Message-Id: %s",
                message["Message-Id"],
            )
            return message["Message-Id"]
        return super().send_email(message, *args, **kwargs)
