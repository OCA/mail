# © 2024 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    use_unassigned_mails = fields.Boolean(
        related="company_id.use_unassigned_mails", readonly=False
    )
    delete_unassigned_after = fields.Integer(
        related="company_id.delete_unassigned_after", readonly=False
    )
    assign_to_same_thread = fields.Boolean(
        related="company_id.assign_to_same_thread", readonly=False
    )
    unassigned_show_after = fields.Boolean(
        related="company_id.unassigned_show_after", readonly=False
    )
