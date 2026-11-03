# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Flow tests for the personal outgoing (Outlook) mail server backport.

These exercise the whole journey rather than each method in isolation:

* a regular user sets up their personal Outlook server from preferences;
* outgoing mail is routed to that server (and never used as a fallback for
  someone else);
* the user switches back to the default server;
* the OAuth callback lets the *owner* (a non-admin) complete the flow and
  activate the server, while a different user is rejected.
"""

import json
from unittest.mock import patch
from urllib.parse import urlencode

from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools import mute_logger

# Expiration well in the future but within PostgreSQL's int4 range (~2033).
_FAKE_TOKENS = ("fake-refresh-token", "fake-access-token", 2000000000)


@tagged("post_install", "-at_install")
class TestPersonalServerFlow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        icp = cls.env["ir.config_parameter"].sudo()
        icp.set_param("base_setup.default_external_email_server", True)
        icp.set_param("microsoft_outlook_client_id", "test-client-id")
        icp.set_param("microsoft_outlook_client_secret", "test-client-secret")
        cls.alice = cls.env["res.users"].create(
            {
                "name": "Alice Tester",
                "login": "alice_outgoing_test",
                "email": "alice@example.com",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.IrMailServer = cls.env["ir.mail_server"].sudo()

    def _personal_servers(self, user):
        return self.IrMailServer.with_context(active_test=False).search(
            [("owner_user_id", "=", user.id)]
        )

    def test_01_setup_creates_personal_server_and_returns_oauth_action(self):
        """Choosing Outlook in preferences creates the personal server and
        returns the Microsoft redirect action."""
        action = (
            self.env["res.users"]
            .with_user(self.alice)
            .action_setup_outgoing_mail_server("outlook")
        )

        server = self._personal_servers(self.alice)
        self.assertEqual(len(server), 1, "exactly one personal server")
        self.assertFalse(server.active, "stays archived until OAuth succeeds")
        self.assertEqual(server.smtp_authentication, "outlook")
        self.assertEqual(server.smtp_host, "smtp.outlook.com")
        self.assertEqual(server.smtp_port, 587)
        self.assertEqual(server.smtp_encryption, "starttls")
        self.assertEqual(server.from_filter, "alice@example.com")
        self.assertEqual(server.smtp_user, "alice@example.com")
        self.assertEqual(server.owner_user_id, self.alice)

        self.assertEqual(action.get("type"), "ir.actions.act_url")
        self.assertTrue(action.get("url"), "a Microsoft login URL is returned")

        # While the server is still archived (OAuth not completed) it is not
        # exposed as the user's server yet, exactly like in Odoo 19.
        self.alice.invalidate_recordset()
        self.assertFalse(self.alice.outgoing_mail_server_id)
        self.assertEqual(self.alice.outgoing_mail_server_type, "default")

        # Simulate a successful OAuth callback (server un-archived).
        server.active = True
        self.alice.invalidate_recordset()
        self.assertEqual(self.alice.outgoing_mail_server_id, server)
        self.assertEqual(self.alice.outgoing_mail_server_type, "outlook")

    def test_02_routing_uses_personal_server_only_for_owner_from(self):
        """The exact `from` address routes to the personal server, but it is
        never picked as a generic fallback for another sender."""
        personal = self.IrMailServer.create(
            {
                "name": "Alice perso",
                "smtp_host": "smtp.outlook.com",
                "smtp_port": 587,
                "smtp_encryption": "starttls",
                "smtp_authentication": "outlook",
                "smtp_user": "alice@example.com",
                "from_filter": "alice@example.com",
                "owner_user_id": self.alice.id,
                "active": True,
            }
        )
        public = self.IrMailServer.create(
            {
                "name": "Public notifications",
                "smtp_host": "smtp.example.com",
                "smtp_port": 25,
                "smtp_encryption": "none",
                "from_filter": False,
                "sequence": 5,
                "active": True,
            }
        )

        # mail.mail hands over the full server set; the personal server is
        # matched by its exact from_filter (step 1).
        all_servers = self.IrMailServer.search([], order="sequence, id")
        server, _from = self.IrMailServer._find_mail_server(
            "alice@example.com", all_servers
        )
        self.assertEqual(server, personal)

        # A different sender must fall back to the public server, never to
        # Alice's personal mailbox.
        server2, _from2 = self.IrMailServer._find_mail_server(
            "bob@other.com", all_servers
        )
        self.assertEqual(server2, public)
        self.assertNotEqual(server2, personal)

        # Direct (mail_servers=None) selection excludes personal servers too.
        self.assertNotIn(
            personal,
            self.IrMailServer.search(
                self.IrMailServer._find_mail_server_allowed_domain()
            ),
        )

    def test_03_switch_back_to_default_removes_personal_server(self):
        users = self.env["res.users"].with_user(self.alice)
        users.action_setup_outgoing_mail_server("outlook")
        self.assertTrue(self._personal_servers(self.alice))

        users.action_setup_outgoing_mail_server("default")
        self.assertFalse(
            self._personal_servers(self.alice),
            "the personal server is removed when going back to default",
        )

    def test_04_gc_removes_stale_personal_server(self):
        stale = self.IrMailServer.create(
            {
                "name": "Stale (old email)",
                "smtp_host": "smtp.outlook.com",
                "from_filter": "old-alice@example.com",
                "owner_user_id": self.alice.id,
                "active": False,
            }
        )
        self.env["res.users"]._gc_personal_mail_servers()
        self.assertFalse(stale.exists(), "archived/orphan personal server is GC'd")


@tagged("post_install", "-at_install")
class TestOutlookOAuthCallbackFlow(HttpCase):
    def setUp(self):
        super().setUp()
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("base_setup.default_external_email_server", True)
        icp.set_param("microsoft_outlook_client_id", "test-client-id")
        icp.set_param("microsoft_outlook_client_secret", "test-client-secret")
        group_user = self.env.ref("base.group_user")
        self.alice = self.env["res.users"].create(
            {
                "name": "Alice OAuth",
                "login": "alice_oauth",
                "password": "alice_oauth_pwd",
                "email": "alice@example.com",
                "groups_id": [(6, 0, [group_user.id])],
            }
        )
        self.bob = self.env["res.users"].create(
            {
                "name": "Bob OAuth",
                "login": "bob_oauth",
                "password": "bob_oauth_pwd",
                "email": "bob@example.com",
                "groups_id": [(6, 0, [group_user.id])],
            }
        )
        self.server = (
            self.env["ir.mail_server"]
            .sudo()
            .create(
                {
                    "name": "Alice personal",
                    "smtp_host": "smtp.outlook.com",
                    "smtp_port": 587,
                    "smtp_encryption": "starttls",
                    "smtp_authentication": "outlook",
                    "smtp_user": "alice@example.com",
                    "from_filter": "alice@example.com",
                    "owner_user_id": self.alice.id,
                    "active": False,
                }
            )
        )

    def _callback_url(self):
        state = json.dumps(
            {
                "model": "ir.mail_server",
                "id": self.server.id,
                "csrf_token": self.server.sudo()._get_outlook_csrf_token(),
            }
        )
        return "/microsoft_outlook/confirm?" + urlencode(
            {"code": "fake-auth-code", "state": state}
        )

    def test_owner_completes_oauth_and_activates_server(self):
        self.authenticate("alice_oauth", "alice_oauth_pwd")
        with patch.object(
            self.env.registry["ir.mail_server"],
            "_fetch_outlook_refresh_token",
            lambda self, code: _FAKE_TOKENS,
        ):
            resp = self.url_open(self._callback_url(), allow_redirects=False)

        self.assertIn(resp.status_code, (302, 303))
        self.assertIn(
            f"/odoo/my-preferences/{self.alice.id}",
            resp.headers.get("Location", ""),
        )

        server = self.env["ir.mail_server"].sudo().browse(self.server.id)
        self.assertTrue(server.active, "server is un-archived after login")
        self.assertEqual(server.microsoft_outlook_refresh_token, _FAKE_TOKENS[0])

    @mute_logger("odoo.addons.mail_user_outgoing_server.controllers.main")
    def test_non_owner_is_forbidden(self):
        self.authenticate("bob_oauth", "bob_oauth_pwd")
        resp = self.url_open(self._callback_url(), allow_redirects=False)
        self.assertEqual(resp.status_code, 403, "another user cannot link it")

        server = self.env["ir.mail_server"].sudo().browse(self.server.id)
        self.assertFalse(server.active, "server stays archived")
        self.assertFalse(server.microsoft_outlook_refresh_token)
