# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.fields import Domain

from odoo.addons.mail.tools.discuss import Store


class ResPartner(models.Model):
    """Update of res.partner class to take into account the gateway."""

    _inherit = "res.partner"

    gateway_channel_ids = fields.One2many(
        "res.partner.gateway.channel", inverse_name="partner_id"
    )

    @api.model
    def _get_channel_invite_domain(self, channel, with_portal_users=False):
        """Only allow inviting members of the gateway users group.

        Core restricts the invitable users through the ``group_public_id`` field,
        but it is only allowed on channels of type ``channel``, so the restriction
        needs to be done here for gateway channels.
        """
        domain = super()._get_channel_invite_domain(
            channel, with_portal_users=with_portal_users
        )
        if channel and channel.channel_type == "gateway":
            gateway_group = self.env.ref("mail_gateway.gateway_user")
            domain &= Domain("user_ids.share", "=", False) & Domain(
                "user_ids.all_group_ids", "in", gateway_group.id
            )
        return domain

    def _store_gateway_channels_fields(self, res: Store.FieldList):
        """Gateway channels through which the partner can be reached."""
        res.attr("name")
        # sudo: res.partner.gateway.channel - technical data needed by the web
        # client, not meant to be restricted by the reader's access rights
        res.many(
            "gateway_channel_ids",
            "_store_gateway_channel_fields",
            sort="id",
            sudo=True,
        )


class ResPartnerGatewayChannel(models.Model):
    _name = "res.partner.gateway.channel"
    _description = "Technical data used to get the gateway author"

    name = fields.Char(related="gateway_id.name")
    partner_id = fields.Many2one(
        "res.partner", required=True, readonly=True, ondelete="cascade"
    )
    gateway_id = fields.Many2one(
        "mail.gateway", required=True, readonly=True, ondelete="cascade"
    )
    gateway_token = fields.Char(readonly=True)
    company_id = fields.Many2one(
        "res.company", related="gateway_id.company_id", store=True
    )

    @api.depends_context("mail_gateway_partner_info")
    def _compute_display_name(self):
        # Be able to tell to which partner belongs the gateway partner channel
        # e.g.: picking it from a selector
        if not self.env.context.get("mail_gateway_partner_info"):
            return super()._compute_display_name()
        for gateway_channel in self:
            gateway_channel.display_name = (
                f"{gateway_channel.partner_id.display_name} ({gateway_channel.name})"
            )

    _unique_partner_gateway = models.Constraint(
        "UNIQUE(partner_id, gateway_id)",
        "Partner can only have one configuration for each gateway.",
    )

    def _store_gateway_channel_fields(self, res: Store.FieldList):
        res.attr("name")
        res.one("gateway_id", "_store_gateway_fields")

    def mail_format(self):
        return [r._mail_format() for r in self]

    def _mail_format(self):
        return {
            "id": self.id,
            "name": self.name,
            "gateway": {
                "id": self.gateway_id.id,
                "name": self.gateway_id.name,
                "type": self.gateway_id.gateway_type,
            },
        }
