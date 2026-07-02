# Copyright 2026 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import fnmatch
import re

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError


class MailRecipientBlockRule(models.Model):
    _name = "mail.recipient.block.rule"
    _description = "Mail Recipient Block Rule"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    pattern_type = fields.Selection(
        selection=[
            ("exact", "Exact email"),
            ("domain", "Domain"),
            ("contains", "Contains"),
            ("wildcard", "Wildcard"),
            ("regex", "Regular expression"),
        ],
        required=True,
        default="contains",
    )
    pattern = fields.Char(required=True)
    notes = fields.Text()

    @api.constrains("pattern", "pattern_type")
    def _check_pattern(self):
        for rule in self:
            if not (rule.pattern or "").strip():
                raise ValidationError(_("The block pattern cannot be empty."))
            if rule.pattern_type == "regex":
                try:
                    re.compile(rule.pattern)
                except re.error as error:
                    raise ValidationError(
                        _("Invalid regular expression: %s", error)
                    ) from error

    def _match_email(self, email):
        self.ensure_one()
        normalized_email = tools.email_normalize(email) or (email or "").lower()
        pattern = (self.pattern or "").strip().lower()
        if not normalized_email or not pattern:
            return False
        if self.pattern_type == "exact":
            return normalized_email == pattern
        if self.pattern_type == "domain":
            domain = normalized_email.rsplit("@", 1)[-1]
            pattern_domain = pattern.lstrip("@")
            return domain == pattern_domain
        if self.pattern_type == "contains":
            return pattern in normalized_email
        if self.pattern_type == "wildcard":
            return fnmatch.fnmatchcase(normalized_email, pattern)
        if self.pattern_type == "regex":
            return bool(re.search(self.pattern, normalized_email, re.I))
        return False

    @api.model
    def _is_blocked_email(self, email):
        return any(rule._match_email(email) for rule in self.search([]))

    @api.model
    def _filter_blocked_recipients(self, recipients):
        allowed = []
        blocked = []
        for recipient in recipients or []:
            normalized_emails = tools.mail.email_normalize_all(recipient)
            emails_to_check = normalized_emails or [recipient]
            if any(self._is_blocked_email(email) for email in emails_to_check):
                blocked.append(recipient)
            else:
                allowed.append(recipient)
        return allowed, blocked
