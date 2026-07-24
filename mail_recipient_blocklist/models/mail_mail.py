# Copyright 2026 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, models, tools

_logger = logging.getLogger(__name__)


class MailMail(models.Model):
    _inherit = "mail.mail"

    def _blocked_recipient_emails(self):
        self.ensure_one()
        emails = []
        emails += tools.mail.email_normalize_all(self.email_to)
        emails += tools.mail.email_normalize_all(self.email_cc)
        emails += self.recipient_ids.mapped("email")
        BlockRule = self.env["mail.recipient.block.rule"]
        return [
            email for email in emails if email and BlockRule._is_blocked_email(email)
        ]

    def _has_only_blocked_recipients(self):
        self.ensure_one()
        emails = []
        emails += tools.mail.email_normalize_all(self.email_to)
        emails += tools.mail.email_normalize_all(self.email_cc)
        emails += self.recipient_ids.mapped("email")
        emails = [email for email in emails if email]
        blocked_emails = self._blocked_recipient_emails()
        return bool(emails) and len(emails) == len(blocked_emails)

    def _cancel_blocked_recipient_delivery(self):
        reason = _("Email delivery blocked by recipient blocklist rules.")
        self.write({"state": "cancel", "failure_reason": reason})
        notifications = (
            self.env["mail.notification"]
            .sudo()
            .search(
                [
                    ("notification_type", "=", "email"),
                    ("mail_mail_id", "in", self.ids),
                    ("notification_status", "not in", ("sent", "canceled")),
                ]
            )
        )
        if notifications:
            notifications.write({"notification_status": "canceled"})

    def _prepare_outgoing_list(
        self, mail_server=False, recipients_follower_status=None
    ):
        email_list = super()._prepare_outgoing_list(
            mail_server=mail_server,
            recipients_follower_status=recipients_follower_status,
        )
        BlockRule = self.env["mail.recipient.block.rule"]
        filtered_email_list = []
        blocked_recipients = []
        for email_values in email_list:
            email_values = dict(email_values)
            email_to, blocked_to = BlockRule._filter_blocked_recipients(
                email_values.get("email_to")
            )
            email_cc, blocked_cc = BlockRule._filter_blocked_recipients(
                email_values.get("email_cc")
            )
            email_values["email_to"] = email_to
            email_values["email_cc"] = email_cc
            email_values["email_to_normalized"] = [
                email
                for email in email_values.get("email_to_normalized", [])
                if not BlockRule._is_blocked_email(email)
            ]
            blocked_recipients += blocked_to + blocked_cc
            if email_to or email_cc:
                filtered_email_list.append(email_values)
        if blocked_recipients:
            _logger.info(
                "Blocked recipient(s) for mail.mail %s: %s",
                self.id,
                ", ".join(blocked_recipients),
            )
        return filtered_email_list

    def send(self, auto_commit=False, raise_exception=False, post_send_callback=None):
        blocked_mails = self.filtered(lambda mail: mail._has_only_blocked_recipients())
        if blocked_mails:
            blocked_mails._cancel_blocked_recipient_delivery()
            _logger.info(
                "Cancelled %s outgoing email(s) addressed only to blocked "
                "recipients: %s",
                len(blocked_mails),
                blocked_mails.ids,
            )
        return super(MailMail, self - blocked_mails).send(
            auto_commit=auto_commit,
            raise_exception=raise_exception,
            post_send_callback=post_send_callback,
        )
