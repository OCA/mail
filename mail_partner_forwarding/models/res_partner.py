from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    forwarding_partner_id = fields.Many2one(
        "res.partner",
        help="Messages are forwarded only for partners who are direct followers, not"
        " for partners who are notified because they belong to a channel following"
        " the thread.",
    )
