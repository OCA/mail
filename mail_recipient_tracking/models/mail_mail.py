# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time
from datetime import datetime, timezone
from email.utils import COMMASPACE

from odoo import fields, models
from odoo.tools.mail import email_split_and_format


class MailMail(models.Model):
    _inherit = "mail.mail"

    def _tracking_email_prepare(self, email):
        """Prepare email.tracking.email record values"""
        ts = time.time()
        dt = datetime.fromtimestamp(ts, timezone.utc)
        # Partners notified in Cc get their own email with an empty "To"
        email_to_list = email.get("email_to") or email.get("email_cc") or []
        email_to = COMMASPACE.join(email_to_list)
        return {
            "name": self.subject,
            "timestamp": f"{ts:.6f}",
            "time": fields.Datetime.to_string(dt),
            "mail_id": self.id,
            "mail_message_id": self.mail_message_id.id,
            "partner_id": (email.get("partner_id") or self.env["res.partner"]).id,
            "recipient": email_to,
            "sender": self.email_from,
        }

    def _prepare_outgoing_list(self, mail_server=False, doc_to_followers=None):
        """Creates the mail.tracking.email record and adds the image tracking
        to the email. Please note that because we can't add mail headers in this
        function, the added tracking image will later (IrMailServer.build_email)
        also be used to extract the mail.tracking.email record id and to set the
        X-Odoo-MailTracking-ID header there.
        """
        emails = super()._prepare_outgoing_list(
            mail_server=mail_server,
            doc_to_followers=doc_to_followers,
        )
        tracking_vals_list = [self._tracking_email_prepare(email) for email in emails]
        trackings = self.env["mail.tracking.email"].sudo().create(tracking_vals_list)
        for email, tracking in zip(emails, trackings, strict=True):
            tracking.tracking_img_add(email)
        return emails

    def _postprocess_sent_message(
        self, success_pids, success_emails, failure_reason=False, failure_type=None
    ):
        # Before super: it may delete the failed emails
        if failure_type:
            self._tracking_email_failed_set(failure_reason, failure_type)
        return super()._postprocess_sent_message(
            success_pids,
            success_emails,
            failure_reason=failure_reason,
            failure_type=failure_type,
        )

    def _tracking_email_failed_set(self, failure_reason, failure_type):
        """Flag the failure of the emails in their trackings, so it is shown in
        the chatter and in the failed lists, and the emails can be sent again:

        - Emails failing before being prepared (e.g. the SMTP server is
          unreachable) have no tracking: create it in error state.
        - Emails failing again after a retry keep the trackings of the former
          failure: flag their message as failed again.
        """
        Tracking = self.env["mail.tracking.email"].sudo()
        failed_states = self.env["mail.message"].get_failed_states()
        trackings = Tracking.search([("mail_id", "in", self.ids)])
        vals_list = []
        for mail in self:
            mail_trackings = trackings.filtered(lambda t, mail=mail: t.mail_id == mail)
            if mail_trackings:
                failed = mail_trackings.filtered(lambda t: t.state in failed_states)
                if failed and not mail.mail_message_id.mail_tracking_needs_action:
                    mail.mail_message_id.mail_tracking_needs_action = True
                    failed._notify_tracking_status_update()
                continue
            error_vals = {
                "state": "error",
                "error_type": failure_type,
                "error_description": failure_reason or mail.failure_reason,
            }
            recipients = [
                {"partner_id": partner, "email_to": [partner.email_formatted]}
                for partner in mail.recipient_ids
            ]
            if mail.email_to or not recipients:
                recipients.append({"email_to": email_split_and_format(mail.email_to)})
            for recipient in recipients:
                vals_list.append(
                    {**mail._tracking_email_prepare(recipient), **error_vals}
                )
        # Not marking partners as bounced: the error isn't due to the recipient
        return Tracking.create(vals_list)
