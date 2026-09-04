# Copyright 2025 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PortalFakeModel(models.Model):
    _name = "portal.fake.model"
    _inherit = ["portal.mixin", "mail.thread", "mail.activity.mixin"]
    _description = "Portal Fake Model"

    name = fields.Char()
    partner_id = fields.Many2one(
        comodel_name="res.partner",
    )
