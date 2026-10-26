# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.mail.tools.discuss import Store


class DiscussChannelMember(models.Model):
    _inherit = "discuss.channel.member"

    def _store_guest_dynamic_fields(self, guest_res: Store.FieldList):
        super()._store_guest_dynamic_fields(guest_res)
        if self.channel_id.channel_type != "gateway":
            return
        # sudo: mail.gateway - gateway through which the guest is writing
        guest_res.one("gateway_id", "_store_gateway_fields", sudo=True)
