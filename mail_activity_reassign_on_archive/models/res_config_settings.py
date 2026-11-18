# Copyright 2026 Reinaldo J. Menendez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    activity_reassign_on_archive = fields.Boolean(
        string="Reassign Activities on User Archive",
        config_parameter="mail_activity_reassign_on_archive.enabled",
        help="When enabled, activities assigned to archived users will be "
        "reassigned to a designated user instead of being deleted.",
    )
    activity_reassign_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Reassign Activities To",
        config_parameter="mail_activity_reassign_on_archive.reassign_user_id",
        domain="[('active', '=', True), ('share', '=', False)]",
        help="User to reassign activities to when the original assignee is archived.",
    )
    activity_reassign_on_unarchive = fields.Boolean(
        string="Restore Activities on User Unarchive",
        config_parameter="mail_activity_reassign_on_archive.restore_on_unarchive",
        help="When enabled, pending activities will be reassigned back to the "
        "original user when they are unarchived.",
    )

    @api.onchange("activity_reassign_on_archive")
    def _onchange_activity_reassign_on_archive(self):
        if not self.activity_reassign_on_archive:
            self.activity_reassign_user_id = False
            self.activity_reassign_on_unarchive = False
