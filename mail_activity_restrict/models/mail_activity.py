"""Restrict mail.activity modifications to the assigned user."""

from odoo import api, models
from odoo.exceptions import AccessError

# Context key that skips only the check of this module for the rest of an
# operation that was already allowed. Its value must be ``_SKIP_RESTRICT``,
# which cannot be sent through RPC, so clients cannot switch the check off.
SKIP_RESTRICT_KEY = "mail_activity_restrict_skip"
_SKIP_RESTRICT = object()


class MailActivity(models.Model):
    """Extend mail.activity access checks for restricted activity types."""

    _inherit = "mail.activity"

    def _with_restrict_skipped(self):
        return self.with_context(**{SKIP_RESTRICT_KEY: _SKIP_RESTRICT})

    def _is_restrict_skipped(self) -> bool:
        return self.env.context.get(SKIP_RESTRICT_KEY) is _SKIP_RESTRICT

    @api.model_create_multi
    def create(self, vals_list):
        # Anybody allowed to create the activity may assign somebody else. Core
        # (and e.g. mail_activity_reminder via action_notify) then writes on the
        # new activity, which the creator no longer "owns": skip only this
        # module's check for that, core access rules still apply.
        activities = super(MailActivity, self._with_restrict_skipped()).create(
            vals_list
        )
        return activities.with_env(self.env)

    def write(self, vals):
        if "user_id" not in vals:
            return super().write(vals)
        # Changing the assignee makes the current user lose the right to modify
        # the activity, while core still writes on it and its document after the
        # change (notification, subscription). Check access on the state before
        # the change, then skip only this module's check for the rest of it.
        self.check_access("write")
        return super(MailActivity, self._with_restrict_skipped()).write(vals)

    def _get_can_write_restrict_allowed_activities(self):
        """Return restricted activities the current user may modify."""
        return self.sudo().filtered_domain([("user_id", "in", (False, self.env.uid))])

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
        if (
            operation not in ("write", "unlink")
            or not self
            or self.env.su
            or self._is_restrict_skipped()
        ):
            return result

        restricted = self.filtered("activity_type_id.can_write_restrict")
        forbidden = restricted - restricted._get_can_write_restrict_allowed_activities()
        if not forbidden:
            return result

        if result and not (forbidden - result[0]):
            return result

        forbidden = result[0] | forbidden if result else forbidden
        return forbidden, lambda: forbidden._make_can_write_restrict_error(operation)
