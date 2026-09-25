# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL

from odoo.addons.mail.tools.discuss import Store


class ResPartner(models.Model):
    """Update of res.partner class to take into account the gateway."""

    _inherit = "res.partner"

    gateway_channel_ids = fields.One2many(
        "res.partner.gateway.channel", inverse_name="partner_id"
    )

    @api.readonly
    @api.model
    def _search_for_channel_invite(self, store, search_term, channel_id=None, limit=30):
        """Only allow inviting members of the gateway users group.

        Core restricts the invitable users through the ``group_public_id`` field,
        but it is only allowed on channels of type ``channel``, so the restriction
        needs to be done here for gateway channels.
        """
        channel = (
            self.env["discuss.channel"].search([("id", "=", int(channel_id))])
            if channel_id
            else self.env["discuss.channel"]
        )
        if channel.channel_type != "gateway":
            return super()._search_for_channel_invite(
                store, search_term, channel_id=channel_id, limit=limit
            )
        gateway_group = self.env.ref("mail_gateway.gateway_user")
        domain = Domain.AND(
            [
                Domain("name", "ilike", search_term)
                | Domain("email", "ilike", search_term),
                [("id", "!=", self.env.user.partner_id.id)],
                [("active", "=", True)],
                [("user_ids", "!=", False)],
                [("user_ids.active", "=", True)],
                [("user_ids.share", "=", False)],
                [("channel_ids", "not in", channel.id)],
                # only users allowed to access gateway channels can be invited
                [("user_ids.all_group_ids", "in", gateway_group.id)],
            ]
        )
        query = self._search(domain, limit=limit)
        # bypass lack of support for case insensitive order in search()
        query.order = SQL(
            'LOWER(%s), "res_partner"."id"', self._field_to_sql(self._table, "name")
        )
        selectable_partners = self.env["res.partner"].browse(query)
        selectable_partners._search_for_channel_invite_to_store(store, channel)
        return {
            "count": self.env["res.partner"].search_count(domain),
            "partner_ids": selectable_partners.ids,
        }

    def _field_store_repr(self, field_name):
        if field_name == "gateway_channels":
            # sudo: res.partner.gateway.channel - technical data needed by the web
            # client, not meant to be restricted by the reader's access rights
            return [
                Store.Attr(
                    "gateway_channels",
                    lambda partner: partner.sudo().gateway_channel_ids.mail_format(),
                )
            ]
        return super()._field_store_repr(field_name)

    def _to_store_defaults(self, target):
        """Add the gateway channels the partner can be reached on."""
        return super()._to_store_defaults(target) + ["gateway_channels"]


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
