"""Extend restricted activities to members of the assigned team."""

from odoo import models
from odoo.exceptions import AccessError


class MailActivity(models.Model):
    """Allow team members to modify restricted activities."""

    _inherit = "mail.activity"

    def _get_can_write_restrict_allowed_activities(self):
        """Allow the assignee and the members of the assigned team."""
        allowed = super()._get_can_write_restrict_allowed_activities()
        unassigned_with_team = self.sudo().filtered(
            lambda activity: not activity.user_id and activity.team_id
        )
        return (allowed - unassigned_with_team) | self.sudo().filtered_domain(
            [("team_id.member_ids", "in", self.env.uid)]
        )

    def _make_can_write_restrict_error(self, operation: str) -> AccessError:
        """Build the access error raised for restricted team activities."""
        if len(self) == 1:
            return AccessError(
                self.env._(
                    "You cannot %(operation)s this activity because only the assigned "
                    "user or members of the assigned team can modify activities of this"
                    " type.",
                    operation=operation,
                )
            )
        return AccessError(
            self.env._(
                "You cannot %(operation)s some activities because only their assigned "
                "user or members of the assigned team can modify activities of this "
                "type.",
                operation=operation,
            )
        )
