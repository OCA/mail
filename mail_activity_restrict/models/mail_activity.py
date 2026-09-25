"""Restrict mail.activity modifications to the assigned user."""

from odoo import models
from odoo.exceptions import AccessError


class MailActivity(models.Model):
    """Extend mail.activity access checks for restricted activity types."""

    _inherit = "mail.activity"

    def _get_can_write_restrict_allowed_activities(self):
        """Return restricted activities the current user may modify."""
        return self.sudo().filtered_domain([("user_id", "=", self.env.uid)])

    def _make_can_write_restrict_error(self, operation: str) -> AccessError:
        """Build the access error raised for restricted activity types."""
        if len(self) == 1:
            return AccessError(
                self.env._(
                    "You cannot %(operation)s this activity because only "
                    "the assigned user can modify activities of this type.",
                    operation=operation,
                )
            )
        return AccessError(
            self.env._(
                "You cannot %(operation)s some activities because only their "
                "assigned user can modify activities of this type.",
                operation=operation,
            )
        )

    def _check_access(self, operation: str) -> tuple | None:
        """Restrict write-like operations when the activity type requires it."""
        result = super()._check_access(operation)
        if operation not in ("write", "unlink") or not self or self.env.su:
            return result

        restricted = self.filtered("activity_type_id.can_write_restrict")
        forbidden = restricted - restricted._get_can_write_restrict_allowed_activities()
        if not forbidden:
            return result

        if result and not (forbidden - result[0]):
            return result

        forbidden = result[0] | forbidden if result else forbidden
        return forbidden, lambda: forbidden._make_can_write_restrict_error(operation)
