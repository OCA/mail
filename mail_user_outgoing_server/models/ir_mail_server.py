# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Backport of the Odoo 19 "personal outgoing mail server" mechanism.

A mail server may belong to a single user (``owner_user_id``). Such a personal
server is:

* used *only* to send the mail authored by its owner (matched by the exact
  ``from`` address in :meth:`_find_mail_server`, step 1);
* never used as a generic fallback for anybody else
  (:meth:`_filter_mail_servers_fallback`) nor as a default public server
  (:meth:`_find_mail_server_allowed_domain`).
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import (
    email_domain_extract,
    email_domain_normalize,
    email_normalize,
)

_logger = logging.getLogger(__name__)


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    owner_user_id = fields.Many2one("res.users", string="Owner", copy=False)

    _sql_constraints = [
        (
            "unique_owner_user_id",
            "UNIQUE(owner_user_id)",
            "A user can only own a single personal outgoing mail server.",
        ),
    ]

    # ------------------------------------------------------------------
    # Mail server selection hooks (backported from Odoo 19)
    # ------------------------------------------------------------------
    @api.model
    def _find_mail_server_allowed_domain(self):
        """Domain restricting which servers may be used as default/public.

        Personal servers (with an owner) are excluded: they may only be used
        through the explicit candidate set built by
        :meth:`mail.mail._filter_mail_mail_servers`.
        """
        return [("owner_user_id", "=", False)]

    @api.model
    def _filter_mail_servers_fallback(self, servers):
        """Remove personal servers from the fallback candidates."""
        return servers.filtered(lambda s: not s.owner_user_id)

    def _find_mail_server(self, email_from, mail_servers=None):
        """Find the appropriate mail server for the given email address.

        Backport of the Odoo 19 version: identical to the v18 core logic with
        two surgical additions, marked ``# BACKPORT`` below.

        Returns: Record<ir.mail_server>, email_from
        """
        email_from_normalized = email_normalize(email_from)
        email_from_domain = email_domain_extract(email_from_normalized)
        notifications_email = self.env.context.get(
            "domain_notifications_email"
        ) or email_normalize(self._get_default_from_address())
        notifications_domain = email_domain_extract(notifications_email)

        if mail_servers is None:
            # BACKPORT: restrict the default search to public servers.
            mail_servers = self.sudo().search(
                self._find_mail_server_allowed_domain(), order="sequence"
            )
        # 0. Archived mail server should never be used
        mail_servers = mail_servers.filtered("active")

        def first_match(target, normalize_method):
            for mail_server in mail_servers:
                if mail_server.from_filter and any(
                    normalize_method(email.strip()) == target
                    for email in mail_server.from_filter.split(",")
                ):
                    return mail_server

        # 1. Try to find a mail server for the right mail from
        # Skip if passed email_from is False (example Odoobot has no email address)
        if email_from_normalized:
            if mail_server := first_match(email_from_normalized, email_normalize):
                return mail_server, email_from

            if mail_server := first_match(email_from_domain, email_domain_normalize):
                return mail_server, email_from

        # BACKPORT: from now on (fallback steps) personal servers are excluded.
        mail_servers = self._filter_mail_servers_fallback(mail_servers)

        # 2. Try to find a mail server for <notifications@domain.com>
        if notifications_email:
            if mail_server := first_match(notifications_email, email_normalize):
                return mail_server, notifications_email

            if mail_server := first_match(notifications_domain, email_domain_normalize):
                return mail_server, notifications_email

        # 3. Take the first mail server without "from_filter" because
        # nothing else has been found... Will spoof the FROM because
        # we have no other choices (will use the notification email if available
        # otherwise we will use the user email)
        if mail_server := mail_servers.filtered(lambda m: not m.from_filter):
            return mail_server[0], notifications_email or email_from

        # 4. Return the first mail server even if it was configured for another domain
        if mail_servers:
            _logger.warning(
                "No mail server matches the from_filter, using %s as fallback",
                notifications_email or email_from,
            )
            return mail_servers[0], notifications_email or email_from

        # 5: SMTP config in odoo-bin arguments
        from_filter = self.env["ir.mail_server"]._get_default_from_filter()

        if self._match_from_filter(email_from, from_filter):
            return None, email_from

        if notifications_email and self._match_from_filter(
            notifications_email, from_filter
        ):
            return None, notifications_email

        _logger.warning(
            "The from filter of the CLI configuration does not match the "
            "notification email or the user email, using %s as fallback",
            notifications_email or email_from,
        )
        return None, notifications_email or email_from

    # ------------------------------------------------------------------
    # Outlook OAuth: allow the owner of a personal server to link it
    # ------------------------------------------------------------------
    def open_microsoft_outlook_uri(self):
        """Allow the owner of a personal server (a non-admin user) to start the
        OAuth flow.

        The v18 core method only allows ``base.group_system`` users, which would
        prevent regular users from connecting their own mailbox.
        """
        self.ensure_one()
        if self.owner_user_id and self.owner_user_id == self.env.user:
            if not self.sudo().is_microsoft_outlook_configured:
                raise UserError(_("Please configure your Outlook credentials."))
            if not self.sudo().microsoft_outlook_uri:
                raise UserError(_("Please configure your Outlook credentials."))
            return {
                "type": "ir.actions.act_url",
                "url": self.sudo().microsoft_outlook_uri,
                "target": "self",
            }
        # Standard admin-managed server: keep the core behaviour.
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(
                _("Only the administrator can link an Outlook mail server.")
            )
        return super().open_microsoft_outlook_uri()
