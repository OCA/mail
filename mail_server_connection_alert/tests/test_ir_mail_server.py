# Copyright 2026 CIT-Services
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, PropertyMock, patch

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestIrMailServerReminders(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_group = cls.env.ref("base.group_system")
        cls.admin_user = cls.env["res.users"].create(
            {
                "name": "Mail Test Admin",
                "login": "mail_test_admin",
                "email": "admin@example.com",
                "groups_id": [(6, 0, [cls.admin_group.id])],
            }
        )

        cls.outgoing_server = cls.env["ir.mail_server"].create(
            {
                "name": "Test Outgoing Server",
                "smtp_host": "smtp.test.com",
                "smtp_port": 25,
                "active": True,
            }
        )

        cls.incoming_server = cls.env["fetchmail.server"].create(
            {
                "name": "Test Incoming Server",
                "server_type": "imap",
                "server": "imap.test.com",
                "active": True,
                "state": "done",
            }
        )

    @mute_logger("odoo.addons.mail_server_connection_alert.models.ir_mail_server")
    def test_process_reminders_detects_failures_and_notifies(self):
        mail_server_cls = type(self.env["ir.mail_server"])
        fetchmail_cls = type(self.env["fetchmail.server"])
        bus_cls = type(self.env["bus.bus"])

        with (
            patch.object(
                mail_server_cls,
                "test_smtp_connection",
                side_effect=Exception("SMTP Auth Failed"),
            ),
            patch.object(
                fetchmail_cls, "connect", side_effect=Exception("IMAP Timeout")
            ),
            patch.object(bus_cls, "_sendone") as mock_sendone,
        ):
            self.env["ir.mail_server"]._process_reminders()

            self.assertTrue(mock_sendone.called)
            sent_types = [call[0][1] for call in mock_sendone.call_args_list]
            self.assertIn("web_notify", sent_types)

            web_notify_payloads = [
                call[0][2]
                for call in mock_sendone.call_args_list
                if call[0][1] == "web_notify"
            ]
            self.assertTrue(web_notify_payloads)
            self.assertTrue(all(p.get("type") == "danger" for p in web_notify_payloads))
            self.assertTrue(all(p.get("html") is True for p in web_notify_payloads))
            self.assertTrue(all(p.get("sticky") is True for p in web_notify_payloads))

            channel = self.env["discuss.channel"].search(
                [("name", "=", "⚠️ System Mail Alerts")], limit=1
            )
            self.assertTrue(channel, "Alert channel should be created.")
            self.assertIn(
                self.admin_user.partner_id,
                channel.channel_partner_ids,
                "Admin partner must be in the channel.",
            )

            latest_message = channel.message_ids.sorted("id", reverse=True)[:1]
            self.assertTrue(latest_message, "A warning message should be posted.")
            self.assertIn("Test Outgoing Server", latest_message.body)
            self.assertIn("Test Incoming Server", latest_message.body)

    @mute_logger("odoo.addons.mail_server_connection_alert.models.ir_mail_server")
    def test_process_reminders_only_incoming_fails(self):
        mail_server_cls = type(self.env["ir.mail_server"])
        fetchmail_cls = type(self.env["fetchmail.server"])
        bus_cls = type(self.env["bus.bus"])

        with (
            patch.object(mail_server_cls, "test_smtp_connection", return_value=True),
            patch.object(
                fetchmail_cls, "connect", side_effect=Exception("IMAP Failure")
            ),
            patch.object(bus_cls, "_sendone") as mock_sendone,
        ):
            self.env["ir.mail_server"]._process_reminders()

            self.assertTrue(mock_sendone.called)
            channel = self.env.ref(
                "mail_server_connection_alert.channel_system_mail_alerts"
            )
            latest_message = channel.message_ids.sorted("id", reverse=True)[:1]
            self.assertTrue(latest_message)
            self.assertIn("Test Incoming Server", latest_message.body)
            self.assertNotIn("Outgoing Mail Server(s)", latest_message.body)

    @mute_logger("odoo.addons.mail_server_connection_alert.models.ir_mail_server")
    def test_process_reminders_no_active_outgoing_server(self):
        self.env["ir.mail_server"].search([("active", "=", True)]).write(
            {"active": False}
        )
        fetchmail_cls = type(self.env["fetchmail.server"])
        bus_cls = type(self.env["bus.bus"])

        with (
            patch.object(fetchmail_cls, "connect", return_value=MagicMock()),
            patch.object(bus_cls, "_sendone") as mock_sendone,
        ):
            self.env["ir.mail_server"]._process_reminders()

            self.assertTrue(mock_sendone.called)
            web_notify_payloads = [
                call[0][2]
                for call in mock_sendone.call_args_list
                if call[0][1] == "web_notify"
            ]
            self.assertTrue(web_notify_payloads)
            self.assertTrue(
                any(
                    "No active outgoing mail servers found" in p.get("message", "")
                    for p in web_notify_payloads
                )
            )

            channel = self.env.ref(
                "mail_server_connection_alert.channel_system_mail_alerts"
            )
            latest_message = channel.message_ids.sorted("id", reverse=True)[:1]
            self.assertTrue(latest_message)
            self.assertIn(
                "No active outgoing mail servers found in system settings.",
                latest_message.body,
            )

    def test_process_reminders_success_no_alerts(self):
        mail_server_cls = type(self.env["ir.mail_server"])
        fetchmail_cls = type(self.env["fetchmail.server"])
        bus_cls = type(self.env["bus.bus"])

        with (
            patch.object(mail_server_cls, "test_smtp_connection", return_value=True),
            patch.object(fetchmail_cls, "connect", return_value=MagicMock()),
            patch.object(bus_cls, "_sendone") as mock_sendone,
        ):
            self.env["ir.mail_server"]._process_reminders()

            mock_sendone.assert_not_called()

    def test_incoming_mail_connection_cleanup_imap(self):
        fetchmail_cls = type(self.env["fetchmail.server"])
        mock_connection = MagicMock()

        with (
            patch.object(
                type(self.env["ir.mail_server"]),
                "test_smtp_connection",
                return_value=True,
            ),
            patch.object(fetchmail_cls, "search", return_value=self.incoming_server),
            patch.object(fetchmail_cls, "connect", return_value=mock_connection),
        ):
            self.env["ir.mail_server"]._process_reminders()

            mock_connection.close.assert_called_once()
            mock_connection.quit.assert_not_called()

    def test_incoming_mail_connection_cleanup_pop(self):
        fetchmail_cls = type(self.env["fetchmail.server"])
        pop_server = self.env["fetchmail.server"].create(
            {
                "name": "Test POP Server",
                "server_type": "pop",
                "server": "pop.test.com",
                "active": True,
                "state": "done",
            }
        )
        mock_connection = MagicMock()

        with (
            patch.object(
                type(self.env["ir.mail_server"]),
                "test_smtp_connection",
                return_value=True,
            ),
            patch.object(fetchmail_cls, "search", return_value=pop_server),
            patch.object(fetchmail_cls, "connect", return_value=mock_connection),
        ):
            self.env["ir.mail_server"]._process_reminders()

            mock_connection.quit.assert_called_once()
            mock_connection.close.assert_not_called()

    @mute_logger("odoo.addons.mail_server_connection_alert.models.ir_mail_server")
    def test_incoming_mail_connection_cleanup_error_handled(self):
        fetchmail_cls = type(self.env["fetchmail.server"])
        mock_connection = MagicMock()
        mock_connection.close.side_effect = Exception("Socket teardown failed")

        with (
            patch.object(
                type(self.env["ir.mail_server"]),
                "test_smtp_connection",
                return_value=True,
            ),
            patch.object(fetchmail_cls, "search", return_value=self.incoming_server),
            patch.object(fetchmail_cls, "connect", return_value=mock_connection),
        ):
            self.env["ir.mail_server"]._process_reminders()
            mock_connection.close.assert_called_once()

    def test_incoming_mail_connection_cleanup_other_type(self):
        fetchmail_cls = type(self.env["fetchmail.server"])
        mock_connection = MagicMock()

        with (
            patch.object(
                type(self.env["ir.mail_server"]),
                "test_smtp_connection",
                return_value=True,
            ),
            patch.object(fetchmail_cls, "search", return_value=self.incoming_server),
            patch.object(fetchmail_cls, "connect", return_value=mock_connection),
            patch.object(
                fetchmail_cls,
                "server_type",
                new_callable=PropertyMock,
                return_value="other",
            ),
        ):
            self.env["ir.mail_server"]._process_reminders()

            mock_connection.close.assert_not_called()
            mock_connection.quit.assert_not_called()

    def test_notify_system_admins_no_admin_users(self):
        failures = {
            "outgoing": {
                "web_notify_data": ["Test"],
                "channel_data": ["<li>Test</li>"],
            },
            "incoming": {"web_notify_data": [], "channel_data": []},
        }
        with (
            patch.object(
                type(self.env.ref("base.group_system")),
                "users",
                new_callable=PropertyMock,
                return_value=self.env["res.users"],
            ),
            patch.object(
                type(self.env["discuss.channel"]), "message_post"
            ) as mock_post,
        ):
            self.env["ir.mail_server"]._notify_system_admins(failures)
            mock_post.assert_not_called()
