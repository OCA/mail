# © 2024 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    use_unassigned_mails = fields.Boolean(string="Allow manual assignment of e-mails")
    delete_unassigned_after = fields.Integer(
        string="Delete Unassigned E-Mails After", default=30
    )
    assign_to_same_thread = fields.Boolean(
        "Assign E-Mails to same Thread in the Wizard"
    )
    unassigned_show_after = fields.Boolean(
        "Show the threads after assigning", default=True
    )
