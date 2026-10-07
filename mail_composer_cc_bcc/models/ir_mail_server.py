# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    def _prepare_email_message(self, message, smtp_session):
        """
        Define smtp_to based on context instead of To+Cc+Bcc
        """
        # Each recipients gets its own email
        # See method `_prepare_outgoing_list`
        is_from_composer = self.env.context.get("is_from_composer", False)
        if is_from_composer:
            # Empty recipients means there is a bug.
            # => refuse to send, otherwise it would
            # - send duplicate emails
            # - leak Bcc
            recipients = self.env.context.get("recipients")
            if not recipients:
                raise ValueError("Could not determine the recipient of this email")
            # Pop before super(): if this email fails,
            # the next one must not get its recipient
            smtp_to = recipients.pop(0)
            _logger.debug("smtp_to: %s", smtp_to)
            if not smtp_to:
                # Recipient without a valid address: `mail.mail._send`
                # skips this email and keeps sending the others
                raise AssertionError(self.NO_VALID_RECIPIENT)

        smtp_from, smtp_to_list, message = super()._prepare_email_message(
            message, smtp_session
        )

        if is_from_composer:
            smtp_to_list = [smtp_to]

        return smtp_from, smtp_to_list, message
