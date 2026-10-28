# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from odoo import fields, models

from odoo.addons.mail.tools.discuss import Store


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    gateway_channel_token = fields.Char()
    anonymous_name = fields.Char()  # Same field we will use on im_livechat
    gateway_id = fields.Many2one("mail.gateway")
    gateway_message_ids = fields.One2many(
        "mail.notification",
        inverse_name="gateway_channel_id",
    )
    company_id = fields.Many2one("res.company", default=False)
    channel_type = fields.Selection(
        selection_add=[("gateway", "Gateway")], ondelete={"gateway": "set default"}
    )
    gateway_token = fields.Char(
        related="gateway_id.token",
        string="Gateway related Token",
        required=False,
    )

    def _to_store(self, store: Store, fields):
        res = super()._to_store(store, fields)
        gw_channels = self.filtered("gateway_id")
        if not gw_channels:
            return res
        # sudo: res.partner.gateway.channel - technical lookup by token, done
        # once for the whole recordset (this runs for every channel on load)
        partner_by_key = {}
        for gw_channel in (
            self.env["res.partner.gateway.channel"]
            .sudo()
            .search(
                [
                    ("gateway_id", "in", gw_channels.gateway_id.ids),
                    (
                        "gateway_token",
                        "in",
                        [t for t in gw_channels.mapped("gateway_channel_token") if t],
                    ),
                ]
            )
        ):
            partner_by_key.setdefault(
                (gw_channel.gateway_id.id, gw_channel.gateway_token),
                gw_channel.partner_id,
            )
        for record in gw_channels:
            guests = record.channel_member_ids.guest_id
            partner = partner_by_key.get(
                (record.gateway_id.id, record.gateway_channel_token),
                self.env["res.partner"],
            )
            store.add_model_values(
                self._name,
                {
                    "id": record.id,
                    "gateway": record.gateway_id._gateway_info(),
                    "gateway_id": record.id,
                    "gateway_partner_id": partner.id,
                    "gateway_guest_id": guests.id if len(guests) == 1 else False,
                },
            )
        return res

    def _get_gateway_partner(self):
        """Partner linked to the gateway token of the channel, if any."""
        self.ensure_one()
        if not self.gateway_id or not self.gateway_channel_token:
            return self.env["res.partner"]
        # sudo: res.partner.gateway.channel - technical lookup by token
        return (
            self.env["res.partner.gateway.channel"]
            .sudo()
            .search(
                [
                    ("gateway_id", "=", self.gateway_id.id),
                    ("gateway_token", "=", self.gateway_channel_token),
                ],
                limit=1,
            )
            .partner_id
        )

    def _get_gateway_guest(self):
        """Guest of the channel when there is exactly one (sender not yet
        linked to a partner), used by the "New Partner" action."""
        self.ensure_one()
        guests = self.channel_member_ids.guest_id
        return guests if len(guests) == 1 else self.env["mail.guest"]

    def _generate_avatar_gateway(self):
        # We will use this function to set a default avatar on each module
        return False

    def _generate_avatar(self):
        if self.channel_type not in ("gateway"):
            return super()._generate_avatar()
        avatar = self._generate_avatar_gateway()
        if not avatar:
            return False
        return base64.b64encode(avatar.encode())

    def message_post(
        self, *, message_type="notification", gateway_type=False, **kwargs
    ):
        message = super().message_post(
            message_type=message_type,
            gateway_type=gateway_type or self.gateway_id.gateway_type,
            **kwargs,
        )
        if (
            self.gateway_id
            and not self.env.context.get("no_gateway_notification", False)
            and message.message_type != "notification"
        ):
            self.env["mail.notification"].create(
                {
                    "mail_message_id": message.id,
                    "gateway_channel_id": self.id,
                    "notification_type": "gateway",
                    "gateway_type": self.gateway_id.gateway_type,
                }
            ).send_gateway()
        return message

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
        res = super()._message_update_content(
            message,
            body=body,
            attachment_ids=attachment_ids,
            partner_ids=partner_ids,
            strict=strict,
            **kwargs,
        )
        if self.channel_type == "gateway" and message.gateway_notification_ids:
            self.env[
                f"mail.gateway.{self.gateway_id.gateway_type}"
            ]._update_content_after_hook(self, message)
        return res
