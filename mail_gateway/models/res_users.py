# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from odoo.addons.mail.tools.discuss import Store


class ResUsers(models.Model):
    _inherit = "res.users"

    gateway_ids = fields.Many2many("mail.gateway")

    def _store_init_global_fields(self, res: Store.FieldList):  # pylint: disable=missing-return
        super()._store_init_global_fields(res)
        res.attr("has_gateway_access", self.has_group("mail_gateway.gateway_user"))
        if not self._is_public():
            # sudo: mail.gateway - name and type of the gateways of the current user
            res.many(
                "gateways",
                "_store_gateway_fields",
                value=self.sudo().gateway_ids,
            )
