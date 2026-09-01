# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class FakePartnerSubDefault(models.Model):
    _name = "fakepartner.subdefault"
    _description = "Fake Model with default partner field name"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True)
    partner_id = fields.Many2one(comodel_name="res.partner")


class FakePartnerSubCustom(models.Model):
    _name = "fakepartner.subcustom"
    _description = "Fake Model with custom partner field name"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True)
    contact_id = fields.Many2one(comodel_name="res.partner")

    def _get_partner_field_name(self):
        """Override to use contact_id instead of the default partner_id."""
        return "contact_id"
