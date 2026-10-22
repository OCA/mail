# Copyright 2026 CIT-Services
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from unittest.mock import MagicMock, patch

from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, tagged

try:
    from odoo.addons.website.tools import MockRequest
except ImportError:
    MockRequest = None

from ..controllers.main import MailTrackingController


@tagged("post_install", "-at_install")
class TestBrevoTracking(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.icp = cls.env["ir.config_parameter"].sudo()
        cls.icp.set_param("brevo.api_key", "test-brevo-api-key-12345")
        cls.icp.set_param("brevo.webhook_token", "test-webhook-token-67890")
        cls.icp.set_param("brevo.webhooks_domain", False)
        cls.icp.set_param("web.base.url", "http://localhost:8069")

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Brevo Partner",
                "email": "brevo_test@example.com",
            }
        )

        cls.mail_message = cls.env["mail.message"].create(
            {
                "subject": "Test Brevo Message",
                "message_id": "<1234567890@test.com>",
            }
        )

        cls.tracking_email = cls.env["mail.tracking.email"].create(
            {
                "partner_id": cls.partner.id,
                "recipient": cls.partner.email,
                "recipient_address": cls.partner.email,
                "mail_message_id": cls.mail_message.id,
                "state": "sent",
            }
        )
        cls.controller = MailTrackingController()

    def test_01_ir_mail_server_headers(self):
        """Test custom tracking header X-Mailin-custom addition."""
        mail_server = self.env["ir.mail_server"]
        headers = mail_server._tracking_headers_add(self.tracking_email.id, {})
        self.assertIn("X-Mailin-custom", headers)
        custom_data = json.loads(headers["X-Mailin-custom"])
        self.assertEqual(custom_data["odoo_db"], self.env.cr.dbname)
        self.assertEqual(custom_data["tracking_email_id"], self.tracking_email.id)

    def test_02_brevo_values(self):
        """Test retrieval of Brevo parameters."""
        params = self.env["mail.tracking.email"]._brevo_values()
        self.assertEqual(params.api_key, "test-brevo-api-key-12345")
        self.assertEqual(params.webhook_token, "test-webhook-token-67890")
        self.assertEqual(params.webhooks_domain, "http://localhost:8069")

        # Test missing API key raises ValidationError
        self.icp.set_param("brevo.api_key", False)
        with self.assertRaises(ValidationError):
            self.env["mail.tracking.email"]._brevo_values()
        self.icp.set_param("brevo.api_key", "test-brevo-api-key-12345")

    def test_03_brevo_event2type(self):
        """Test mapping of Brevo event names to mail.tracking.event states."""
        mte = self.env["mail.tracking.email"]
        self.assertEqual(mte._brevo_event2type({"event": "delivered"}), "delivered")
        self.assertEqual(mte._brevo_event2type({"event": "opened"}), "open")
        self.assertEqual(mte._brevo_event2type({"event": "clicks"}), "click")
        self.assertEqual(mte._brevo_event2type({"event": "soft_bounce"}), "soft_bounce")
        self.assertEqual(mte._brevo_event2type({"event": "softBounce"}), "soft_bounce")
        self.assertEqual(mte._brevo_event2type({"event": "hard_bounce"}), "hard_bounce")
        self.assertEqual(mte._brevo_event2type({"event": "hardBounce"}), "hard_bounce")
        self.assertEqual(mte._brevo_event2type({"event": "spam"}), "spam")
        self.assertEqual(mte._brevo_event2type({"event": "blocked"}), "reject")
        self.assertEqual(mte._brevo_event2type({"event": "unknown_event"}), "UNKNOWN")

    def test_04_brevo_event_process(self):
        """Test processing of Brevo webhook event payload."""
        event_payload = {
            "event": "delivered",
            "email": "brevo_test@example.com",
            "id": 99901,
            "ts_event": 1725278400,
            "message-id": "<1234567890@test.com>",
            "X-Mailin-custom": json.dumps(
                {
                    "odoo_db": self.env.cr.dbname,
                    "tracking_email_id": self.tracking_email.id,
                }
            ),
        }
        self.env["mail.tracking.email"]._brevo_event_process(event_payload, {})
        self.tracking_email.invalidate_recordset()
        self.assertEqual(self.tracking_email.state, "delivered")

        # Test event deduplication
        expected_brevo_id = (
            f"{event_payload['message-id']}_{event_payload['event']}"
            f"_{event_payload['ts_event']}"
        )
        event_count = self.env["mail.tracking.event"].search_count(
            [("brevo_id", "=", expected_brevo_id)]
        )
        self.assertEqual(event_count, 1)

        # Reprocess same event
        self.env["mail.tracking.email"]._brevo_event_process(event_payload, {})
        event_count_after = self.env["mail.tracking.event"].search_count(
            [("brevo_id", "=", expected_brevo_id)]
        )
        self.assertEqual(event_count_after, 1)

    @patch("requests.get")
    def test_05_manual_check_brevo(self, mock_get):
        """Test manual sync button logic action_manual_check_brevo."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "events": [
                {
                    "event": "opened",
                    "email": "brevo_test@example.com",
                    "id": 99902,
                    "ts_event": 1725278500,
                    "messageId": "<1234567890@test.com>",
                }
            ]
        }
        mock_get.return_value = mock_response

        self.tracking_email.action_manual_check_brevo()
        self.tracking_email.invalidate_recordset()
        self.assertEqual(self.tracking_email.state, "opened")

    @patch("requests.get")
    @patch("requests.put")
    def test_06_partner_brevo_actions(self, mock_put, mock_get):
        """Test partner bounce checking, setting, and unsetting."""
        # Test brevo_check_email_bounced
        mock_get_res = MagicMock()
        mock_get_res.status_code = 200
        mock_get_res.json.return_value = {"emailBlacklisted": True}
        mock_get.return_value = mock_get_res

        self.partner.brevo_check_email_bounced()
        self.partner.invalidate_recordset()
        self.assertTrue(self.partner.email_bounced)

        # Test force_unset_bounced
        mock_put_res = MagicMock()
        mock_put_res.status_code = 200
        mock_put.return_value = mock_put_res

        self.partner.force_unset_bounced()
        self.partner.invalidate_recordset()
        self.assertFalse(self.partner.email_bounced)

        # Test force_set_bounced
        self.partner.force_set_bounced()
        self.partner.invalidate_recordset()
        self.assertTrue(self.partner.email_bounced)

    @patch("requests.post")
    @patch("requests.get")
    @patch("requests.delete")
    def test_07_res_config_settings_webhooks(self, mock_del, mock_get, mock_post):
        """Test webhook registration and unregistration in settings."""
        wizard = self.env["res.config.settings"].create({})

        # Test registration
        mock_post_res = MagicMock()
        mock_post_res.status_code = 201
        mock_post.return_value = mock_post_res

        wizard.mail_tracking_brevo_register_webhooks()
        mock_post.assert_called_once()

        # Test unregistration
        mock_get_res = MagicMock()
        mock_get_res.status_code = 200
        mock_get_res.json.return_value = {
            "webhooks": [
                {
                    "id": 12,
                    "url": "http://localhost:8069/mail/tracking/brevo/all?db="
                    + self.env.cr.dbname,
                }
            ]
        }
        mock_get.return_value = mock_get_res

        mock_del_res = MagicMock()
        mock_del_res.status_code = 204
        mock_del.return_value = mock_del_res

        wizard.mail_tracking_brevo_unregister_webhooks()
        mock_del.assert_called_once()

    @patch("odoo.addons.mail_tracking_brevo.controllers.main.ensure_db")
    def test_08_brevo_controller_endpoint(self, mock_ensure_db):
        """Test Brevo webhook controller logic directly."""
        payload = {
            "event": "opened",
            "email": "brevo_test@example.com",
            "id": 99903,
            "ts_event": 1725278600,
            "message-id": "<1234567890@test.com>",
            "X-Mailin-custom": json.dumps(
                {
                    "odoo_db": self.env.cr.dbname,
                    "tracking_email_id": self.tracking_email.id,
                }
            ),
        }

        if MockRequest:
            with MockRequest(self.env) as request:
                request.get_json_data = lambda: payload
                request.params = {
                    "db": self.env.cr.dbname,
                    "token": "test-webhook-token-67890",
                }
                request.make_response = lambda text, headers: text
                res = self.controller.mail_tracking_brevo_webhook(
                    token="test-webhook-token-67890"
                )
                self.assertIn("OK", str(res))
                self.tracking_email.invalidate_recordset()
                self.assertEqual(self.tracking_email.state, "opened")
        else:
            self.env["mail.tracking.email"]._brevo_event_process(payload, {})
            self.tracking_email.invalidate_recordset()
            self.assertEqual(self.tracking_email.state, "opened")
