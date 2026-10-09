# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Self-service setup of a personal outgoing mail server (Outlook only).

Backport of the Odoo 19 ``res.users`` additions, merged with the
``microsoft_outlook`` bridge (this backport only supports Outlook).
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import config, email_normalize


class ResUsers(models.Model):
    _inherit = "res.users"

    outgoing_mail_server_id = fields.Many2one(
        "ir.mail_server",
        compute="_compute_outgoing_mail_server_id",
        groups="base.group_user",
    )
    outgoing_mail_server_type = fields.Selection(
        [("default", "Default"), ("outlook", "Outlook")],
        compute="_compute_outgoing_mail_server_id",
        required=True,
        default="default",
        groups="base.group_user",
    )
    has_external_mail_server = fields.Boolean(
        compute="_compute_has_external_mail_server"
    )

    def _compute_has_external_mail_server(self):
        external = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("base_setup.default_external_email_server")
        )
        for user in self:
            user.has_external_mail_server = bool(external)

    @api.depends("email")
    def _compute_outgoing_mail_server_id(self):
        IrMailServer = self.env["ir.mail_server"].sudo()
        for user in self:
            server = IrMailServer.search(
                [
                    ("from_filter", "ilike", "_@_"),
                    "|",
                    "|",
                    ("from_filter", "=", user.email_normalized),
                    ("smtp_user", "=", user.email),
                    ("owner_user_id", "=", user._origin.id),
                ],
                limit=1,
            )
            user.outgoing_mail_server_id = server.id
            user.outgoing_mail_server_type = (
                server.smtp_authentication
                if server.smtp_authentication == "outlook"
                else "default"
            )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            "has_external_mail_server",
            "outgoing_mail_server_id",
            "outgoing_mail_server_type",
        ]

    # ------------------------------------------------------------------
    # Personal mail server lifecycle
    # ------------------------------------------------------------------
    @api.autovacuum
    def _gc_personal_mail_servers(self):
        """Delete orphan/stale personal servers (e.g. after an email change)."""
        self.env["ir.mail_server"].with_context(active_test=False).search(
            [("owner_user_id", "!=", False)]
        ).filtered(
            lambda s: s.owner_user_id.outgoing_mail_server_id != s or not s.active
        ).unlink()

    @api.model
    def _get_mail_server_values(self, server_type):
        if server_type == "outlook":
            return {
                "smtp_host": "smtp.outlook.com",
                "smtp_authentication": "outlook",
            }
        return {}

    @api.model
    def _get_mail_server_setup_end_action(self, smtp_server):
        if smtp_server.smtp_authentication == "outlook":
            return smtp_server.sudo().open_microsoft_outlook_uri()
        raise UserError(_("Unsupported mail server type."))

    @api.model
    def action_setup_outgoing_mail_server(self, server_type):
        """Configure the personal outgoing mail server of the current user."""
        user = self.env.user
        if not user.has_external_mail_server:
            raise UserError(_("You are not allowed to create a personal mail server."))
        if not user._is_internal():
            raise UserError(
                _("Only internal users can configure a personal mail server.")
            )

        existing_mail_server = (
            self.env["ir.mail_server"]
            .sudo()
            .with_context(active_test=False)
            .search([("owner_user_id", "=", user.id)])
        )

        if server_type == "default":
            if existing_mail_server:
                existing_mail_server.unlink()
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "message": _("Switching back to the default server."),
                    "type": "warning",
                },
            }

        email = user.email
        if not email:
            raise UserError(
                _("Please set your email before connecting your mail server.")
            )

        normalized_email = email_normalize(email)
        # Inlined equivalent of v19's ir.mail_server._parse_from_filter (absent in v18)
        parsed_from_filter = [
            part.strip() for part in (normalized_email or "").split(",") if part.strip()
        ]
        if (
            not normalized_email
            or "@" not in normalized_email
            or parsed_from_filter != [normalized_email]
        ):
            raise UserError(_("Wrong email address %s.", email))

        # The user's email must not be served by an alias domain, otherwise we
        # would leak the outgoing emails of that domain.
        alias_domain = self.env["mail.alias.domain"].sudo().search([])
        cli_default_from = config.get("email_from")
        match_from_filter = self.env["ir.mail_server"]._match_from_filter
        if any(
            match_from_filter(e, normalized_email)
            for e in alias_domain.mapped("default_from_email")
        ) or (
            cli_default_from and match_from_filter(cli_default_from, normalized_email)
        ):
            raise UserError(
                _(
                    "Your email address is used by an alias domain, and so you "
                    "can not create a mail server for it."
                )
            )

        if (
            server_type == user.outgoing_mail_server_type
            and user.outgoing_mail_server_id.from_filter == normalized_email
            and user.outgoing_mail_server_id.smtp_user == normalized_email
        ):
            # Re-connect the existing account
            return self._get_mail_server_setup_end_action(user.outgoing_mail_server_id)

        if existing_mail_server:
            existing_mail_server.unlink()

        values = {
            # Un-archived by the OAuth callback once the login succeeds; stale
            # pending servers are removed by the GC autovacuum.
            "active": False,
            "name": _("%s's outgoing email", user.name),
            "smtp_user": normalized_email,
            "smtp_pass": False,
            "from_filter": normalized_email,
            "smtp_port": 587,
            "smtp_encryption": "starttls",
            "owner_user_id": user.id,
            **self._get_mail_server_values(server_type),
        }
        smtp_server = self.env["ir.mail_server"].sudo().create(values)
        return self._get_mail_server_setup_end_action(smtp_server)

    @api.model
    def action_test_outgoing_mail_server(self):
        user = self.env.user
        if not user.has_external_mail_server:
            raise UserError(_("You are not allowed to test personal mail servers."))
        if not user._is_internal():
            raise UserError(
                _("Only internal users can configure personal mail servers.")
            )

        server_sudo = user.outgoing_mail_server_id.sudo()
        if not server_sudo:
            raise UserError(_("No mail server configured"))
        server_sudo.test_smtp_connection()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": _("Connection Test Successful!"),
                "type": "success",
            },
        }
