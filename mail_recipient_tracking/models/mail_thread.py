# Copyright 2019 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from email.utils import getaddresses

from lxml import etree

from odoo import api, fields, models
from odoo.tools.mail import email_split_and_format_normalize


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    failed_message_ids = fields.One2many(
        "mail.message",
        "res_id",
        string="Failed Messages",
        domain=lambda self: [("model", "=", self._name)]
        + self._get_failed_message_domain(),
    )

    def _get_message_create_valid_field_names(self):
        valid_field_names = super()._get_message_create_valid_field_names()
        return valid_field_names | {"email_to", "email_cc"}

    def _get_failed_message_domain(self):
        """Domain used to display failed messages on the 'failed_messages'
        widget"""
        failed_states = self.env["mail.message"].get_failed_states()
        return [
            ("mail_tracking_needs_action", "=", True),
            ("mail_tracking_ids.state", "in", list(failed_states)),
        ]

    @api.model
    def _message_route_process(self, message, message_dict, routes):
        """Adds CC recipient to the message.

        Because Odoo implementation avoid store 'from, to, cc' recipients we
        ensure that this information its written into the mail.message record.
        """
        message_dict.update(
            {
                "email_cc": message_dict.get("cc", False),
                "email_to": message_dict.get("to", False),
            }
        )
        return super()._message_route_process(message, message_dict, routes)

    def _routing_handle_bounce(self, email_message, message_dict):
        bounced_message = message_dict["bounced_message"]
        mail_trackings = bounced_message.mail_tracking_ids.filtered(
            lambda x: x.recipient_address == message_dict["bounced_email"]
            or (
                message_dict["bounced_partner"]
                and message_dict["bounced_partner"] == x.partner_id
            )
        )
        if mail_trackings:
            # TODO detect hard of soft bounce
            mail_trackings.event_create("soft_bounce", message_dict)
        return super()._routing_handle_bounce(email_message, message_dict)

    def _message_add_suggested_recipients(self, force_primary_email=False):
        suggested = super()._message_add_suggested_recipients(
            force_primary_email=force_primary_email
        )
        for record in self:
            self._add_extra_recipients_suggestions(record, suggested, "email_cc")
            self._add_extra_recipients_suggestions(record, suggested, "email_to")
        return suggested

    def _add_extra_recipients_suggestions(self, record, suggestions, field_mail):
        email_extra_formatted_list = []
        emails_extra = record.message_ids.mapped(field_mail)
        for email in emails_extra:
            email_extra_formatted_list.extend(email_split_and_format_normalize(email))
        email_extra_formatted_list = set(email_extra_formatted_list)
        email_extra_list = [x[1] for x in getaddresses(email_extra_formatted_list)]
        for email in email_extra_list:
            if email not in suggestions[record.id]["email_to_lst"]:
                suggestions[record.id]["email_to_lst"] += (
                    email_split_and_format_normalize(email)
                )

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        """Add filters for failed messages.

        These filters will show up on any search views of any
        model inheriting from ``mail.thread``.
        """
        res = super().get_view(view_id, view_type, **options)
        if view_type != "search":
            return res
        doc = etree.XML(res["arch"])
        # Modify view to add new filter element
        nodes = doc.xpath("//search")
        if nodes:
            # Create filter element
            new_filter = etree.Element(
                "filter",
                {
                    "string": self.env._("Failed sent messages"),
                    "name": "failed_message_ids",
                    "domain": str(
                        [
                            [
                                "failed_message_ids.mail_tracking_ids.state",
                                "in",
                                list(self.env["mail.message"].get_failed_states()),
                            ],
                            [
                                "failed_message_ids.mail_tracking_needs_action",
                                "=",
                                True,
                            ],
                        ]
                    ),
                },
            )
            nodes[0].append(etree.Element("separator"))
            nodes[0].append(new_filter)
        res["arch"] = etree.tostring(doc, encoding="unicode")
        return res
