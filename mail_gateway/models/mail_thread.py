# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from collections import defaultdict

from odoo import models

from odoo.addons.mail.tools.discuss import Store


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _get_message_create_valid_field_names(self):
        # Add gateway fields
        field_names = super()._get_message_create_valid_field_names()
        field_names.update(
            {"gateway_type", "gateway_notifications", "gateway_message_id"}
        )
        return field_names

    def _get_notify_valid_parameters(self):
        notify_valid_parameters = super()._get_notify_valid_parameters()
        return notify_valid_parameters | {"gateway_notifications"}

    def _notify_thread_by_email(self, message, recipients_data, **kwargs):
        partners_data = [r for r in recipients_data if r["notif"] == "gateway"]
        if partners_data:
            self._notify_thread_by_gateway(message, partners_data, **kwargs)
        return super()._notify_thread_by_email(message, recipients_data, **kwargs)

    def _notify_thread_by_gateway(self, message, partners_data, **kwargs):
        for partner_data in partners_data:
            if partner_data["notif"] != "gateway" or not partner_data.get(
                "gateway_channel_id"
            ):
                continue
            message._send_to_gateway_thread(
                self.env["res.partner.gateway.channel"]
                .sudo()
                .browse(partner_data.get("gateway_channel_id"))
            )

    def _notify_get_recipients(self, message, **kwargs):
        if self.env.context.get("link_gateway_message"):
            # When we have the context link_gateway_message we want to avoid
            # notify the followers thread.
            return []
        if kwargs.get("gateway_notifications"):
            result = []
            for notification in kwargs["gateway_notifications"]:
                if not notification.get("channel_type"):
                    continue
                partner = self.env["res.partner"].browse(notification["partner_id"])
                user = partner.user_ids
                follower_data = {
                    "active": partner.active,
                    "email_normalized": partner.email_normalized,
                    "id": partner.id,
                    "is_cc": False,
                    "is_follower": True,
                    "name": partner.name,
                    "lang": partner.lang,
                    "groups": set(user.group_ids.ids),
                    "notif": notification.get("channel_type"),
                    "share": partner.partner_share,
                    "uid": user[:1].id,
                    "ushare": user and any(user.mapped("share")),
                    "gateway_channel_id": notification.get("gateway_channel_id"),
                }
                if follower_data["ushare"]:  # any type of share user
                    follower_data["type"] = "portal"
                elif follower_data[
                    "share"
                ]:  # no user, is share -> customer (partner only)
                    follower_data["type"] = "customer"
                else:  # has a user not share -> internal user
                    follower_data["type"] = "user"
                result.append(follower_data)
            return result
        return super()._notify_get_recipients(message, **kwargs)

    def _store_thread_fields(self, res: Store.FieldList, *, request_list, **kwargs):
        super()._store_thread_fields(res, request_list=request_list, **kwargs)
        if "followers" not in request_list or not self.env.user.has_group(
            "mail_gateway.gateway_user"
        ):
            return
        # sudo: mail.followers - technical data used to know which followers can
        # be reached through a gateway
        followers = (
            self.env["mail.followers"]
            .sudo()
            .search_fetch(
                [("res_id", "in", self.ids), ("res_model", "=", self._name)],
                ["res_id", "partner_id"],
            )
        )
        partners_by_res_id = defaultdict(lambda: self.env["res.partner"])
        for follower in followers:
            partners_by_res_id[follower.res_id] |= follower.partner_id
        res.many(
            "gateway_followers",
            "_store_gateway_channels_fields",
            value=lambda thread: partners_by_res_id[thread.id].filtered(
                "gateway_channel_ids"
            ),
            sudo=True,
        )

    def _check_can_update_message_content(self, messages):
        # We can delete the messages comming from a gateway on not channels
        if self._name != "discuss.channel":
            new_messages = messages.filtered(lambda r: not r.gateway_message_ids)
        else:
            new_messages = messages
        return super()._check_can_update_message_content(new_messages)

    def _message_update_content(
        self,
        message,
        /,
        *,
        body,
        attachment_ids=None,
        partner_ids=None,
        strict=True,
        **kwargs,
    ):
        result = super()._message_update_content(
            message,
            body=body,
            attachment_ids=attachment_ids,
            partner_ids=partner_ids,
            strict=strict,
            **kwargs,
        )
        if body == "":
            # Unlink the message
            for gateway_msg in message.gateway_message_ids:
                # sudo: mail.message - the user may not be the author of the
                # gateway message, they only remove the link to the record
                gateway_msg.sudo().gateway_message_id = False
                Store(bus_channel=gateway_msg).add(
                    gateway_msg,
                    {"gateway_thread_data": gateway_msg.sudo().gateway_thread_data},
                )
        return result

    def _get_allowed_message_params(self):
        return super()._get_allowed_message_params() | {"gateway_notifications"}
