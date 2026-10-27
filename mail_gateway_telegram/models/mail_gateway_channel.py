# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.tools.misc import file_open


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def _generate_avatar_gateway(self):
        if self.gateway_id.gateway_type == "telegram":
            with file_open("mail_gateway_telegram/static/description/icon.svg") as f:
                return f.read()
        return super()._generate_avatar_gateway()
