# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2019 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from email.utils import getaddresses

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import email_split

from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = "mail.message"

    # Recipients
    email_cc = fields.Char(
        "Cc", help='Additional recipients that receive a "Carbon Copy" of the e-mail'
    )
    email_to = fields.Char("To", help="Raw TO recipients")
    mail_tracking_ids = fields.One2many(
        comodel_name="mail.tracking.email",
        inverse_name="mail_message_id",
        bypass_search_access=True,
        string="Mail Trackings",
    )
    mail_tracking_needs_action = fields.Boolean(
        help="The message tracking will be considered to filter tracking issues",
        default=False,
    )
    is_failed_message = fields.Boolean(
        compute="_compute_is_failed_message",
        search="_search_is_failed_message",
    )

    @api.model
    def get_failed_states(self):
        """The 'failed' states of the message"""
        return {"error", "rejected", "spam", "bounced", "soft-bounced"}

    @api.depends(
        "mail_tracking_needs_action",
        "author_id",
        "notification_ids",
        "mail_tracking_ids",
        "mail_tracking_ids.state",
    )
    # The value depends on the active user: do not share it between users
    @api.depends_context("uid")
    def _compute_is_failed_message(self):
        """Compute 'is_failed_message' field for the active user"""
        failed_states = self.get_failed_states()
        for message in self:
            needs_action = message.mail_tracking_needs_action
            involves_me = self.env.user.partner_id in (
                message.author_id | message.notification_ids.res_partner_id
            )
            has_failed_trackings = failed_states.intersection(
                message.mapped("mail_tracking_ids.state")
            )
            message.is_failed_message = bool(
                needs_action and involves_me and has_failed_trackings
            )

    @api.model
    def _search_is_failed_message(self, operator, operand):
        """Search for messages considered failed for the active user.
        Be notice that 'notificacion_ids' is a record that change if
        the user mark the message as readed.
        """
        pid = self.env.user.partner_id.id
        self.flush_model(
            ["author_id", "mail_tracking_ids", "mail_tracking_needs_action"]
        )
        self.env["mail.notification"].flush_model(["mail_message_id", "res_partner_id"])
        self.env["mail.tracking.email"].flush_model(["state"])
        is_involve = Domain.OR(
            [
                [
                    ("notification_ids.res_partner_id", "=", pid),
                ],
                [
                    ("author_id", "=", pid),
                ],
            ]
        )
        domain = Domain.AND(
            [
                [
                    ("mail_tracking_ids.state", "in", list(self.get_failed_states())),
                    ("mail_tracking_needs_action", "=", True),
                ],
                is_involve,
            ]
        )
        # The ORM always calls this method with ("in" | "not in", [True])
        return domain if operator == "in" else ~domain

    def _tracking_status_map_get(self):
        """Map tracking states to be used in chatter"""
        return {
            "False": "waiting",
            "error": "error",
            "deferred": "sent",
            "sent": "sent",
            "delivered": "delivered",
            "opened": "opened",
            "rejected": "error",
            "spam": "error",
            "unsub": "opened",
            "bounced": "error",
            "soft-bounced": "error",
        }

    def _partner_tracking_status_get(self, tracking_email):
        """Determine tracking status"""
        tracking_status_map = self._tracking_status_map_get()
        status = "unknown"
        if tracking_email:
            tracking_email_status = str(tracking_email.state)
            status = tracking_status_map.get(tracking_email_status, "unknown")
        return status

    def _partner_tracking_status_human_get(self, status):
        """Translations for tracking statuses to be used on qweb"""
        statuses = {
            "waiting": self.env._("Waiting"),
            "error": self.env._("Error"),
            "sent": self.env._("Sent"),
            "delivered": self.env._("Delivered"),
            "opened": self.env._("Opened"),
            "unknown": self.env._("Unknown"),
        }
        return self.env._("Status: %s", statuses[status])

    @api.model
    def _get_error_description(self, tracking):
        """Translations for error descriptions to be used on qweb"""
        descriptions = {
            "no_recipient": self.env._("The partner doesn't have a defined email"),
        }
        return descriptions.get(tracking.error_type, tracking.error_description)

    def tracking_status(self):
        """Generates a complete status tracking of the messages by partner"""
        self.ensure_one()
        tracking_delta = 0
        partner_trackings = []
        partners_already = self.env["res.partner"]
        partners = self.env["res.partner"]
        trackings = (
            self.env["mail.tracking.email"]
            .sudo()
            .search([("mail_message_id", "=", self.id)])
        )
        # String to List
        email_cc_list = self._drop_aliases(email_split(self.email_cc))
        email_to_list = self._drop_aliases(email_split(self.email_to))
        # Search related partners recipients
        partners |= partners.search([("email", "in", email_cc_list + email_to_list)])
        # Operate over set's instead of lists
        email_cc_list = set(email_cc_list)
        email_to_list = set(email_to_list) - email_cc_list
        # Search all trackings for this message
        for tracking in trackings:
            status = self._partner_tracking_status_get(tracking)
            recipient = tracking.partner_id.name or tracking.recipient
            partner_trackings.append(
                {
                    "status": status,
                    "status_human": self._partner_tracking_status_human_get(status),
                    "error_type": tracking.error_type,
                    "error_description": self._get_error_description(tracking),
                    "tracking_id": tracking.id,
                    "recipient": recipient,
                    "partner_id": tracking.partner_id.id,
                    "isCc": bool(tracking.partner_id & self.partner_cc_ids),
                    "tracking_delta": f"{self.id}-{tracking_delta}",
                }
            )
            if tracking.partner_id:
                # Discard mails with tracking
                email_cc_list.discard(tracking.partner_id.email)
                email_to_list.discard(tracking.partner_id.email)
                partners_already |= tracking.partner_id
            tracking_delta += 1
        # Search all partner recipients for this message
        if self.partner_ids:
            partners |= self.partner_ids
        if self.notified_partner_ids:
            partners |= self.notified_partner_ids
        # Partners in Cc (since 20.0 they get their own email)
        partners |= self.partner_cc_ids
        # Discard partner recipients already included
        partners -= partners_already
        # Default tracking values
        tracking_unknown_values = {
            "status": "unknown",
            "status_human": self._partner_tracking_status_human_get("unknown"),
            "error_type": False,
            "error_description": False,
            "tracking_id": False,
        }
        # Process tracking status of partner recipients without tracking
        for partner in partners:
            # Discard 'To' with partner
            if partner.email in email_to_list:
                email_to_list.discard(partner.email)
            # If there is partners not included, then status is 'unknown'
            # and perhaps a Cc recipient
            isCc = partner in self.partner_cc_ids
            if partner.email in email_cc_list:
                email_cc_list.discard(partner.email)
                isCc = True
            tracking_status = tracking_unknown_values.copy()
            tracking_status.update(
                {
                    "recipient": partner.name,
                    "partner_id": partner.id,
                    "isCc": isCc,
                    "tracking_delta": f"{self.id}-{tracking_delta}",
                }
            )
            partner_trackings.append(tracking_status)
            tracking_delta += 1
        # Process Cc/To recipients without partner
        for cc, lst in [(True, email_cc_list), (False, email_to_list)]:
            for email in lst:
                tracking_status = tracking_unknown_values.copy()
                tracking_status.update(
                    {
                        "recipient": email,
                        "partner_id": False,
                        "isCc": cc,
                        "tracking_delta": f"{self.id}-{tracking_delta}",
                    }
                )
                partner_trackings.append(tracking_status)
                tracking_delta += 1
        return partner_trackings

    @api.model
    def _drop_aliases(self, mail_list):
        aliases = self.env["mail.alias"].get_aliases()
        if self.env.company.mail_tracking_show_aliases:
            IrConfigParamObj = self.env["ir.config_parameter"].sudo()
            aliases = "{}@{}".format(
                IrConfigParamObj.get_str("mail.catchall.alias"),
                IrConfigParamObj.get_str("mail.catchall.domain"),
            )

        def _filter_alias(email):
            email_wn = getaddresses([email])[0][1]
            if email_wn not in aliases:
                return email_wn

        return list(filter(_filter_alias, mail_list))

    def _prepare_dict_failed_message(self):
        """Preare values to be used by the chatter widget"""
        self.ensure_one()
        failed_trackings = self.mail_tracking_ids.filtered(
            lambda x: x.state in self.get_failed_states()
        )
        if not failed_trackings or not self.mail_tracking_needs_action:
            return
        failed_partners = failed_trackings.mapped("partner_id")
        failed_recipients = failed_partners.read(["display_name"])
        return {
            "id": self.id,
            "date": self.date,
            "body": self.body,
            "failed_recipients": failed_recipients,
        }

    def get_failed_messages(self):
        """Returns the list of failed messages to be used by the
        failed_messages widget"""
        return [
            msg._prepare_dict_failed_message()
            for msg in self.sorted("date", reverse=True)
        ]

    def set_need_action_done(self):
        """This will mark the messages to be ignored in the tracking issues filter"""
        self.check_access("read")
        self.mail_tracking_needs_action = False
        # Refresh the web client data of the current user: the message leaves the
        # chatter "Failed messages" list and the messaging menu "Failed" tab.
        Store(bus_channel=self.env.user).add(
            self, ["mail_tracking_needs_action", "is_failed_message"]
        )

    def _get_failed_trackings(self):
        """Trackings of the messages in a failed state"""
        failed_states = self.get_failed_states()
        return self.sudo().mail_tracking_ids.filtered(
            lambda tracking: tracking.state in failed_states
        )

    def _get_retryable_failed_mails(self):
        """Outgoing emails of the failed trackings that can be queued again.

        The core keeps the failed ``mail.mail`` records only for delivery errors
        (e.g. SMTP errors); invalid or missing recipient emails are removed.
        """
        return self._get_failed_trackings().mail_id.filtered(
            lambda mail: mail.state == "exception"
        )

    def _can_retry_failed_mails(self):
        """Messages pending review with failed recipients can be sent again"""
        self.ensure_one()
        return bool(self.mail_tracking_needs_action and self._get_failed_trackings())

    def action_retry_failed_mails(self):
        """Send again the failed emails of the messages pending review.

        The message leaves the failed lists. If the email fails again, the new
        tracking flags it back as needing action.

        :return: number of emails sent again
        """
        self.check_access("read")
        # Only the author or a notified partner can retry, as in the web client
        messages = self.filtered("is_failed_message")
        count = sum(message._retry_failed_mails() for message in messages)
        if not count:
            return 0
        messages.sudo().mail_tracking_needs_action = False
        self.env.ref("mail.ir_cron_mail_scheduler_action")._trigger()
        Store(bus_channel=self.env.user).add(
            messages,
            {
                "mail_tracking_needs_action": False,
                "is_failed_message": False,
                "can_retry_failed_mails": False,
            },
        )
        return count

    def _retry_failed_mails(self):
        """Send again the failed emails of the message.

        The emails still kept with a delivery error are queued again. For the
        other failed recipients the email is generated again, as the former
        ``mail.resend.message`` wizard did (removed in 20.0).

        :return: number of emails sent again
        """
        self.ensure_one()
        trackings = self._get_failed_trackings()
        # sudo: mail.mail - the user can read the message the emails come from
        mails = self._get_retryable_failed_mails()
        mails.action_retry()
        to_resend = trackings.filtered(lambda tracking: not tracking.mail_id & mails)
        partners = to_resend.partner_id - mails.recipient_ids
        emails = set(
            to_resend.filtered(lambda tracking: not tracking.partner_id).mapped(
                "recipient_address"
            )
        ) - {False, ""}
        return len(mails) + self._resend_failed_recipients(partners, emails)

    def _resend_failed_recipients(self, partners, emails):
        """Generate again the email of the message for the given recipients

        :param partners: <res.partner> recipients to send the email again
        :param emails: set of email addresses of the recipients without partner
        :return: number of recipients the email is sent again
        """
        self.ensure_one()
        message = self.sudo()
        Model = self.env.get(message.model) if message.model else None
        if Model is not None and message.res_id and "message_ids" in Model._fields:
            record = Model.sudo().browse(message.res_id).exists()
        else:
            record = self.env["mail.thread"].sudo()
        recipients_data = []
        if partners:
            partners_data = self.env["mail.followers"]._get_recipient_data(
                self.env["mail.thread"], "user_notification", False, partners.ids
            )[0]
            for pdata in partners_data.values():
                if pdata["id"] not in partners.ids or not pdata["active"]:
                    continue
                # The failed recipients were notified by email
                recipients_data.append(dict(pdata, notif="email", is_cc=False))
        recipients_data += [
            {
                "active": True,
                "email_normalized": email,
                "id": False,
                "is_cc": False,
                "is_follower": False,
                "name": email,
                "lang": False,
                "groups": [],
                "notif": "email",
                "share": True,
                "type": "customer",
                "uid": False,
                "ushare": False,
            }
            for email in emails
        ]
        if not recipients_data:
            return 0
        # The core allows a single notification per message and partner
        resent_pids = {pdata["id"] for pdata in recipients_data if pdata["id"]}
        message.notification_ids.filtered(
            lambda notif: (
                notif.notification_type == "email"
                and (
                    notif.res_partner_id.id in resent_pids
                    or (not notif.res_partner_id and notif.mail_email_address in emails)
                )
            )
        ).unlink()
        record._notify_thread_by_email(message, recipients_data, force_send=False)
        return len(recipients_data)

    @api.model
    def get_failed_count(self):
        """Gets the number of failed messages used on discuss mailbox item"""
        return self.search_count([("is_failed_message", "=", True)])

    @api.model
    def get_failed_messsage_info(self, ids, model):
        msg_ids = self.search([("res_id", "=", ids), ("model", "=", model)])
        res = [
            msg._prepare_dict_failed_message()
            for msg in msg_ids.sorted("date", reverse=True)
            if msg._prepare_dict_failed_message()
        ]
        return res

    def _store_notification_fields(self, res: Store.FieldList):
        """Also send the tracking status in the notification status updates
        (see `_notify_message_notification_update`)"""
        result = super()._store_notification_fields(res)
        res.attr("partner_trackings", lambda message: message.tracking_status())
        res.extend(["mail_tracking_needs_action", "is_failed_message"])
        res.attr(
            "can_retry_failed_mails",
            lambda message: message._can_retry_failed_mails(),
        )
        return result

    def _store_extra_fields(self, res: Store.FieldList, *, format_reply):
        result = super()._store_extra_fields(res, format_reply=format_reply)
        res.attr("partner_trackings", lambda message: message.tracking_status())
        res.extend(["mail_tracking_needs_action", "is_failed_message"])
        res.attr(
            "can_retry_failed_mails",
            lambda message: message._can_retry_failed_mails(),
            # Only messages pending review can show the "Retry" button
            predicate=lambda message: message.mail_tracking_needs_action,
        )
        return result
