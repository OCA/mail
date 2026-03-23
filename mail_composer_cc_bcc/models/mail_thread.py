# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

from .mail_mail import format_emails_str


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    # ------------------------------------------------------------
    # MAIL.MESSAGE HELPERS
    # ------------------------------------------------------------

    def _get_message_create_valid_field_names(self):
        """
        add cc and bcc field to create record in mail.mail
        """
        field_names = super()._get_message_create_valid_field_names()
        field_names.update({"recipient_cc_ids", "recipient_bcc_ids"})
        return field_names

    # ------------------------------------------------------
    # NOTIFICATION API
    # ------------------------------------------------------

    def _notify_by_email_get_base_mail_values(
        self, message, recipients_data, additional_values=None
    ):
        """
        This is to add cc, bcc addresses to mail.mail objects so that email
        can be sent to those addresses.
        """
        res = super()._notify_by_email_get_base_mail_values(
            message, recipients_data, additional_values=additional_values
        )
        context = self.env.context
        skip_adding_cc_bcc = context.get("skip_adding_cc_bcc", False)
        if skip_adding_cc_bcc:
            return res

        partners_cc = context.get("partner_cc_ids", None)
        if partners_cc:
            res["email_cc"] = format_emails_str(partners_cc)

        partners_bcc = context.get("partner_bcc_ids", None)
        if partners_bcc:
            res["email_bcc"] = format_emails_str(partners_bcc)

        return res

    def _notify_get_recipients(self, message, msg_vals=False, **kwargs):
        """
        This is to add cc, bcc recipients so that they can be grouped with
        other recipients.
        """
        ResPartner = self.env["res.partner"]
        rdata = super()._notify_get_recipients(message, msg_vals, **kwargs)
        context = self.env.context
        is_from_composer = context.get("is_from_composer", False)
        skip_adding_cc_bcc = context.get("skip_adding_cc_bcc", False)
        if not is_from_composer or skip_adding_cc_bcc:
            return rdata
        for pdata in rdata:
            pdata["type"] = "customer"
        partners_cc_bcc = context.get("partner_cc_ids", ResPartner)
        partners_cc_bcc += context.get("partner_bcc_ids", ResPartner)

        already_included = {r["id"] for r in rdata if r.get("id")}

        for partner in partners_cc_bcc:
            if not partner.id or partner.id in already_included:
                continue
            already_included.add(partner.id)
            rdata.append(
                {
                    "active": partner.active,
                    "email_normalized": partner.email_normalized or "",
                    "id": partner.id,
                    "is_follower": False,
                    "name": partner.name or "",
                    "lang": partner.lang or False,
                    "groups": [],
                    "notif": "email",
                    "share": True,
                    "type": "customer",
                    "uid": False,
                    "ushare": False,
                }
            )
        return rdata

    def _notify_get_recipients_classify(
        self, message, recipients_data, model_description, msg_vals=False
    ):
        res = super()._notify_get_recipients_classify(
            message, recipients_data, model_description, msg_vals=msg_vals
        )
        is_from_composer = self.env.context.get("is_from_composer", False)
        skip_adding_cc_bcc = self.env.context.get("skip_adding_cc_bcc", False)
        if not is_from_composer or skip_adding_cc_bcc:
            return res
        all_recipients_data = []
        all_recipients_ids = []
        all_recipients_emails = []
        customer_data = None
        for group_data in res:
            if group_data.get("notification_group_name") == "customer":
                customer_data = group_data
            all_recipients_data.extend(group_data.get("recipients_data", []))
            all_recipients_ids.extend(group_data.get("recipients_ids", []))
            all_recipients_emails.extend(group_data.get("recipients_emails", []))
        if not customer_data:
            if not res:
                return res
            customer_data = res[0]
        customer_data["notification_group_name"] = "customer"
        customer_data["recipients_data"] = all_recipients_data
        customer_data["recipients_ids"] = all_recipients_ids
        customer_data["recipients_emails"] = all_recipients_emails
        return [customer_data]

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        if message.message_type == "notification":
            self = self.with_context(skip_adding_cc_bcc=True)
        return super()._notify_thread(message, msg_vals, **kwargs)
