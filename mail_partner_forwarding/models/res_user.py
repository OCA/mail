from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    forwarding_partner_id = fields.Many2one(
        related="partner_id.forwarding_partner_id", readonly=False, user_writeable=True
    )
