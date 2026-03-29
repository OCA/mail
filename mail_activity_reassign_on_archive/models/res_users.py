# Copyright 2026 Reinaldo J. Menendez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class ResUsers(models.Model):
    _inherit = "res.users"

    def action_archive(self):
        """Reassign activities instead of deleting when feature is enabled."""
        enabled, reassign_user_id, _restore = self._get_activity_reassign_config()
        if enabled:
            if not reassign_user_id:
                raise ValidationError(
                    _(
                        "Activity reassignment is enabled but no reassign user is "
                        "configured. Please configure a reassign user in Settings."
                    )
                )
            self._reassign_activities_on_archive(reassign_user_id)
        return super().action_archive()

    def _get_activity_reassign_config(self):
        """Get activity reassign configuration from system parameters."""
        get_param = self.env["ir.config_parameter"].sudo().get_param
        enabled = safe_eval(
            get_param("mail_activity_reassign_on_archive.enabled", "False")
        )
        restore_enabled = safe_eval(
            get_param("mail_activity_reassign_on_archive.restore_on_unarchive", "False")
        )
        user_id = safe_eval(
            get_param("mail_activity_reassign_on_archive.reassign_user_id", "False")
        )
        reassign_user_id = (
            self.env["res.users"].sudo().browse(user_id).exists() if user_id else False
        )
        return enabled, reassign_user_id, restore_enabled

    def _reassign_activities_on_archive(self, reassign_user_id):
        """Helper method to reassign activities to a new user."""
        if not reassign_user_id or not reassign_user_id.active:
            raise ValidationError(
                _("The user designated for activity reassignment must be active.")
            )
        if reassign_user_id.id in self.ids:
            raise ValidationError(
                _("You cannot archive a user designated for activity reassignment.")
            )
        users_to_process = self.filtered(lambda u: u.id != reassign_user_id.id)
        if not users_to_process:
            return
        activities = (
            self.env["mail.activity"]
            .sudo()
            .search(
                [
                    ("user_id", "in", users_to_process.ids),
                ]
            )
        )
        activities.reassign_to_user(reassign_user_id)

    def action_unarchive(self):
        """Restore activities to original users when enabled."""
        result = super().action_unarchive()
        enabled, _reassign_user, restore_enabled = self._get_activity_reassign_config()

        if enabled and restore_enabled:
            activities = (
                self.env["mail.activity"]
                .sudo()
                .search(
                    [
                        ("original_user_id", "in", self.ids),
                    ]
                )
            )
            activities.restore_to_original_user()
        return result
