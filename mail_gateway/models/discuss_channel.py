# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.tools import BinaryBytes

from odoo.addons.mail.tools.discuss import Store


def is_gateway_channel(channel):
    return channel.channel_type == "gateway"


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

    def _store_channel_fields(self, res: Store.FieldList):  # pylint: disable=missing-return
        super()._store_channel_fields(res)
        # sudo: mail.gateway - name and type of the gateway of an accessible channel
        res.one(
            "gateway_id",
            "_store_gateway_fields",
            predicate=is_gateway_channel,
            sudo=True,
        )
        res.attr("anonymous_name", predicate=is_gateway_channel)
        if res.is_for_internal_users():
            # sudo: res.partner.gateway.channel - technical data to know which contact
            # is behind the gateway channel
            res.one(
                "gateway_partner_id",
                ["name"],
                value=lambda channel: channel.sudo()._get_gateway_partner(),
                predicate=is_gateway_channel,
            )

    def _get_gateway_partner(self):
        """Return the contact linked to the gateway channel, if any."""
        self.ensure_one()
        if not self.gateway_id or not self.gateway_channel_token:
            return self.env["res.partner"]
        return (
            self.env["res.partner.gateway.channel"]
            .search(
                [
                    ("gateway_id", "=", self.gateway_id.id),
                    ("gateway_token", "=", self.gateway_channel_token),
                ],
                limit=1,
            )
            .partner_id
        )

    def _generate_avatar_gateway(self):
        # We will use this function to set a default avatar on each module
        return False

    def _generate_avatar(self):
        if self.channel_type not in ("gateway"):
            return super()._generate_avatar()
        avatar = self._generate_avatar_gateway()
        if not avatar:
            return False
        return BinaryBytes(avatar.encode())

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
