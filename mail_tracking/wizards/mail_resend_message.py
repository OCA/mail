# Copyright 2019 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, api, models

# Map between the error types stored in mail.tracking.email and the failure
# types understood by mail.notification
TRACKING_FAILURE_TYPES = {
    "no_recipient": "mail_email_missing",
    "MailDeliveryException": "mail_smtp",
    "SMTPServerDisconnected": "mail_smtp",
    "SMTPSenderRefused": "mail_smtp",
    "SMTPRecipientsRefused": "mail_email_invalid",
}


class MailResendMessage(models.TransientModel):
    _inherit = "mail.resend.message"

    def _tracking_notification_get(self, mail_message, tracking):
        """Return the notification of the tracking recipient, creating it if missing.

        ``mail.resend.partner`` requires a ``mail.notification``, but plenty of
        failed trackings have none: messages sent outside of the notification
        system (``email_outgoing`` ones, like invoices sent by mail) never get
        notifications, and extra recipients (Cc, raw ``email_to``...) aren't
        notified either. Creating the missing notification is what allows those
        recipients to be resent at all.
        """
        if not tracking.partner_id:
            # An email notification can't exist without a partner
            return self.env["mail.notification"]
        notification = mail_message.notification_ids.filtered(
            lambda x, tracking=tracking: x.res_partner_id == tracking.partner_id
        )[:1]
        if notification:
            return notification
        return (
            self.env["mail.notification"]
            .sudo()
            .create(
                {
                    "mail_message_id": mail_message.id,
                    "res_partner_id": tracking.partner_id.id,
                    "notification_type": "email",
                    "notification_status": "exception",
                    "failure_type": TRACKING_FAILURE_TYPES.get(
                        tracking.error_type, "unknown"
                    ),
                    "failure_reason": tracking.error_description,
                }
            )
        )

    @api.model
    def default_get(self, fields):
        rec = super().default_get(fields)
        message_id = self._context.get("mail_message_to_resend")
        if not message_id:
            return rec
        mail_message = self.env["mail.message"].browse(message_id)
        failed_states = self.env["mail.message"].get_failed_states()
        tracking_ids = mail_message.mail_tracking_ids.filtered(
            lambda x: x.state in failed_states
        )
        if tracking_ids:
            # Recipients that mail.notification already prepared in super()
            prepared_partners = mail_message.notification_ids.filtered(
                lambda x: x.notification_type == "email"
                and x.notification_status in ("exception", "bounce")
            ).res_partner_id
            partner_values = []
            for tracking in tracking_ids:
                if tracking.partner_id in prepared_partners:
                    # Create only resends that mail.notification didn't prepare
                    continue
                notification = self._tracking_notification_get(mail_message, tracking)
                if not notification:
                    # Nothing to resend to: recipient without partner
                    continue
                prepared_partners |= notification.res_partner_id
                partner_values.append(
                    {
                        "notification_id": notification.id,
                        "resend": True,
                        "message": tracking.error_description,
                    }
                )
            if partner_values:
                partner_ids = self.env["mail.resend.partner"].create(partner_values).ids
                partner_commands = [
                    Command.link(partner_id) for partner_id in partner_ids
                ]
                rec["partner_ids"].extend(partner_commands)
        return rec

    def resend_mail_action(self):
        for wizard in self:
            to_send = wizard.partner_ids.filtered("resend").mapped("partner_id")
            if to_send:
                # Set as reviewed
                wizard.mail_message_id.mail_tracking_needs_action = False
                # Reset mail.tracking.email state
                tracking_ids = wizard.mail_message_id.mail_tracking_ids.filtered(
                    lambda x, to_send=to_send: x.partner_id in to_send
                )
                tracking_ids.sudo().write({"state": False})
        return super().resend_mail_action()
