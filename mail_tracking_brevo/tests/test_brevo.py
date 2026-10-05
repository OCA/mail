# Copyright 2026 CIT-Services
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from unittest.mock import MagicMock, patch

import requests
from werkzeug.exceptions import NotAcceptable

from odoo import SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

from odoo.addons.website.tools import MockRequest

from .. import __manifest__  # noqa: F401
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
        cls.icp.set_param("brevo.webhooks_registered", False)
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

    def test_ir_mail_server_headers(self):
        mail_server = self.env["ir.mail_server"]
        headers = mail_server._tracking_headers_add(self.tracking_email.id, {})
        self.assertIn("X-Mailin-custom", headers)

        custom_data = json.loads(headers["X-Mailin-custom"])
        self.assertEqual(custom_data["odoo_db"], self.env.cr.dbname)
        self.assertEqual(custom_data["tracking_email_id"], self.tracking_email.id)

    def test_brevo_values(self):
        params = self.env["mail.tracking.email"]._brevo_values()
        self.assertEqual(params.api_key, "test-brevo-api-key-12345")
        self.assertEqual(params.webhook_token, "test-webhook-token-67890")
        self.assertEqual(params.webhooks_domain, "http://localhost:8069")

        self.icp.set_param("brevo.webhooks_domain", "https://example.com")
        params_custom = self.env["mail.tracking.email"]._brevo_values()
        self.assertEqual(params_custom.webhooks_domain, "https://example.com")
        self.icp.set_param("brevo.webhooks_domain", False)

        self.icp.set_param("brevo.api_key", False)
        with self.assertRaises(ValidationError):
            self.env["mail.tracking.email"]._brevo_values()
        self.icp.set_param("brevo.api_key", "test-brevo-api-key-12345")

    def test_brevo_event2type(self):
        mte = self.env["mail.tracking.email"]
        from ..models.mail_tracking_email import EQUIVALENTS

        for event_name, expected_type in EQUIVALENTS.items():
            self.assertEqual(
                mte._brevo_event2type({"event": event_name}), expected_type
            )
            self.assertEqual(mte._brevo_event2type(event_name), expected_type)
        self.assertEqual(mte._brevo_event2type({"event": "unknown_event"}), "UNKNOWN")
        self.assertEqual(mte._brevo_event2type("unknown_event"), "UNKNOWN")

    def test_brevo_country_search(self):
        mte = self.env["mail.tracking.email"]
        country_us = self.env["res.country"].search([("code", "=", "US")], limit=1)
        self.assertEqual(mte._brevo_country_search("us"), country_us.id)
        self.assertEqual(mte._brevo_country_search("US"), country_us.id)
        self.assertFalse(mte._brevo_country_search("XX"))
        self.assertFalse(mte._brevo_country_search(False))
        self.assertFalse(mte._brevo_country_search(None))

    def test_brevo_metadata(self):
        mte = self.env["mail.tracking.email"]

        meta_delivered = mte._brevo_metadata(
            "delivered",
            {
                "message-id": "<msg1@test.com>",
                "event": "delivered",
                "ts_event": "invalid_ts",
                "date": "2026-09-02T12:00:00Z",
                "email": "user@example.com",
                "ip": "1.2.3.4",
                "user_agent": "Mozilla/5.0",
                "link": "https://example.com",
                "device_type": "mobile",
                "country": "US",
            },
            {},
        )
        self.assertEqual(meta_delivered["recipient"], "user@example.com")
        self.assertEqual(meta_delivered["ip"], "1.2.3.4")
        self.assertEqual(meta_delivered["user_agent"], "Mozilla/5.0")
        self.assertEqual(meta_delivered["url"], "https://example.com")
        self.assertTrue(meta_delivered["mobile"])
        self.assertTrue(meta_delivered.get("timestamp"))

        meta_bounce = mte._brevo_metadata(
            "soft_bounce",
            {
                "date": "2026-09-02 12:00:00",
                "reason": "Mailbox full",
                "error": "550 Mailbox full",
            },
            {},
        )
        self.assertEqual(meta_bounce["error_type"], "soft_bounce")
        self.assertEqual(meta_bounce["error_description"], "Mailbox full")
        self.assertEqual(meta_bounce["error_details"], "550 Mailbox full")

        meta_blocked = mte._brevo_metadata(
            "blocked",
            {
                "date": "invalid-date",
                "reason": "Policy rejection",
                "error": "Blocked by admin",
            },
            {},
        )
        self.assertEqual(meta_blocked["error_type"], "rejected")
        self.assertEqual(meta_blocked["error_description"], "Policy rejection")
        self.assertEqual(meta_blocked["error_details"], "Blocked by admin")

        meta_spam = mte._brevo_metadata(
            "spam",
            {
                "ts_event": 1725278400,
                "email": "user@example.com",
            },
            {},
        )
        self.assertEqual(meta_spam["error_type"], "spam")
        self.assertIn("user@example.com", meta_spam["error_description"])

        meta_extra = mte._brevo_metadata(
            "invalid_email",
            {
                "date": "2026-09-02 12:00:00",
                "reason": "Invalid email address",
                "device_type": "tablet",
            },
            {},
        )
        self.assertEqual(meta_extra["error_type"], "invalid_email")
        self.assertTrue(meta_extra["mobile"])

        meta_error = mte._brevo_metadata(
            "error",
            {"reason": "Error reason", "error": "Error details"},
            {},
        )
        self.assertEqual(meta_error["error_type"], "rejected")

        meta_complaint = mte._brevo_metadata(
            "complaint",
            {"email": "complaint@example.com", "ts": 1725278400},
            {},
        )
        self.assertEqual(meta_complaint["error_type"], "spam")
        self.assertEqual(meta_complaint["timestamp"], 1725278400.0)

        meta_empty = mte._brevo_metadata("unknown", {}, {})
        self.assertEqual(meta_empty.get("brevo_id"), "__")
        self.assertNotIn("timestamp", meta_empty)

    def test_brevo_extract_event_ts(self):
        mte = self.env["mail.tracking.email"]

        self.assertEqual(
            mte._brevo_extract_event_ts({"ts_event": 1725278400}), 1725278400.0
        )
        self.assertGreater(
            mte._brevo_extract_event_ts(
                {"ts_event": "invalid", "date": "2026-09-02T12:00:00Z"}
            ),
            0,
        )
        self.assertGreater(
            mte._brevo_extract_event_ts({"date": "2026-09-02 12:00:00"}), 0
        )
        self.assertEqual(mte._brevo_extract_event_ts({"date": "not-a-date"}), 0.0)
        self.assertEqual(mte._brevo_extract_event_ts({}), 0.0)

    def test_brevo_event_process(self):
        mte = self.env["mail.tracking.email"]
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
        mte._brevo_event_process(event_payload, {})
        self.tracking_email.invalidate_recordset()
        self.assertEqual(self.tracking_email.state, "delivered")

        expected_brevo_id = (
            f"{event_payload['message-id']}_{event_payload['event']}"
            f"_{event_payload['ts_event']}"
        )
        self.assertEqual(
            self.env["mail.tracking.event"].search_count(
                [("brevo_id", "=", expected_brevo_id)]
            ),
            1,
        )

        mte._brevo_event_process(event_payload, {})
        self.assertEqual(
            self.env["mail.tracking.event"].search_count(
                [("brevo_id", "=", expected_brevo_id)]
            ),
            1,
        )

        self.assertIsNotNone(
            mte._brevo_event_process(
                {
                    "event": "delivered",
                    "X-Mailin-custom": "invalid json {",
                    "message-id": "<1234567890@test.com>",
                },
                {},
            )
        )
        self.assertIsNotNone(
            mte._brevo_event_process(
                {
                    "event": "delivered",
                    "X-Mailin-custom": 12345,
                    "message-id": "<1234567890@test.com>",
                },
                {},
            )
        )
        with mute_logger("odoo.addons.mail_tracking_brevo.models.mail_tracking_email"):
            self.assertIsNone(
                mte._brevo_event_process(
                    {
                        "event": "delivered",
                        "custom_data": {"odoo_db": "different_db_name"},
                    },
                    {},
                )
            )

        msg_2 = self.env["mail.message"].create(
            {
                "subject": "Lookup Test",
                "message_id": "<lookup_by_msg_id@test.com>",
            }
        )
        tracking_2 = mte.create(
            {
                "partner_id": self.partner.id,
                "recipient": self.partner.email,
                "mail_message_id": msg_2.id,
                "state": "sent",
            }
        )
        mte._brevo_event_process(
            {
                "event": "delivered",
                "message-id": "<lookup_by_msg_id@test.com>",
                "ts_event": 1725278700,
            },
            {},
        )
        tracking_2.invalidate_recordset()
        self.assertEqual(tracking_2.state, "delivered")

        self.assertIsNone(
            mte._brevo_event_process(
                {
                    "event": "delivered",
                    "message-id": "<completely_unknown_msg@test.com>",
                },
                {},
            )
        )

        tracking_2.write({"state": "opened"})
        mte._brevo_event_process(
            {
                "event": "delivered",
                "message-id": "<lookup_by_msg_id@test.com>",
                "ts_event": 1725278800,
            },
            {},
        )
        tracking_2.invalidate_recordset()
        self.assertEqual(tracking_2.state, "opened")

        # Event with no message-id and no tracking_email_id
        self.assertIsNone(
            mte._brevo_event_process({"event": "delivered", "ts_event": 1725278899}, {})
        )

        # Event with camelCase messageId
        mte._brevo_event_process(
            {
                "event": "delivered",
                "messageId": "<lookup_by_msg_id@test.com>",
                "ts_event": 1725278850,
            },
            {},
        )

        # Event with tracking_email_id that does not exist falling back to messageId
        mte._brevo_event_process(
            {
                "event": "delivered",
                "custom_data": {"tracking_email_id": 99999999},
                "messageId": "<lookup_by_msg_id@test.com>",
                "ts_event": 1725278860,
            },
            {},
        )

        # Event with completely empty dict (brevo_id is empty, branch 212->219)
        self.assertIsNone(mte._brevo_event_process({}, {}))

    @patch("requests.get")
    def test_manual_check_brevo(self, mock_get):
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

        mock_err = MagicMock(status_code=500)
        mock_get.return_value = mock_err
        with self.assertRaises(UserError):
            self.tracking_email.action_manual_check_brevo()

        mock_empty = MagicMock(status_code=200)
        mock_empty.json.return_value = {"events": []}
        mock_get.return_value = mock_empty
        with self.assertRaises(UserError):
            self.tracking_email.action_manual_check_brevo()

        events_p1 = [
            {
                "event": "delivered",
                "email": "brevo_test@example.com",
                "messageId": "<1234567890@test.com>",
                "ts_event": 1725278000 + i,
                "custom_data": {"tracking_email_id": self.tracking_email.id},
            }
            for i in range(50)
        ]
        mock_resp_p1 = MagicMock(status_code=200)
        mock_resp_p1.json.return_value = {"events": events_p1}

        mock_resp_p2 = MagicMock(status_code=200)
        mock_resp_p2.json.return_value = {"events": []}

        mock_get.reset_mock()
        mock_get.side_effect = [mock_resp_p1, mock_resp_p2]

        self.tracking_email.action_manual_check_brevo()
        self.assertEqual(mock_get.call_count, 2)

        # Event with unmatched messageId (branch 339->317) and string tracking_id
        events_filter = [
            {
                "event": "delivered",
                "email": "brevo_test@example.com",
                "messageId": "<unrelated_msg@test.com>",
                "ts_event": 1725278100,
            },
            {
                "event": "delivered",
                "email": "brevo_test@example.com",
                "messageId": "<1234567890@test.com>",
                "ts_event": 1725278101,
                "custom_data": f'{{"tracking_email_id":"{self.tracking_email.id}"}}',
            },
        ]
        mock_resp_filter = MagicMock(status_code=200)
        mock_resp_filter.json.return_value = {"events": events_filter}
        mock_get.reset_mock()
        mock_get.side_effect = [mock_resp_filter, mock_resp_p2]
        self.tracking_email.action_manual_check_brevo()

        # Tracking without recipient (branch 304->306)
        tracking_no_recipient = self.env["mail.tracking.email"].create(
            {
                "partner_id": self.partner.id,
                "mail_message_id": self.mail_message.id,
                "recipient": False,
            }
        )
        mock_get.reset_mock()
        mock_get.side_effect = [mock_response, mock_resp_p2]
        tracking_no_recipient.action_manual_check_brevo()

        # Tracking without message_id (filtered out by action_manual_check_brevo)
        tracking_no_msg = self.env["mail.tracking.email"].create(
            {
                "partner_id": self.partner.id,
            }
        )
        tracking_no_msg.action_manual_check_brevo()

    @patch("requests.get")
    @patch("requests.put")
    def test_partner_brevo_actions(self, mock_put, mock_get):
        mock_get_res = MagicMock(status_code=200)
        mock_get_res.json.return_value = {"emailBlacklisted": True}
        mock_get.return_value = mock_get_res

        self.partner.brevo_check_email_bounced()
        self.partner.invalidate_recordset()
        self.assertTrue(self.partner.email_bounced)

        mock_get.return_value = MagicMock(status_code=404)
        self.partner.brevo_check_email_bounced()
        self.partner.invalidate_recordset()
        self.assertFalse(self.partner.email_bounced)

        mock_put.return_value = MagicMock(status_code=200)
        self.partner.brevo_force_unset_bounced()
        self.partner.invalidate_recordset()
        self.assertFalse(self.partner.email_bounced)

        self.partner.brevo_force_set_bounced()
        self.partner.invalidate_recordset()
        self.assertTrue(self.partner.email_bounced)

        # Status 500 on check
        mock_get.return_value = MagicMock(status_code=500)
        self.partner.brevo_check_email_bounced()

        # Partner without email
        partner_no_email_actions = self.env["res.partner"].create(
            {"name": "No Email Partner 2", "email": False}
        )
        partner_no_email_actions.brevo_check_email_bounced()
        partner_no_email_actions.brevo_force_set_bounced()
        partner_no_email_actions.brevo_force_unset_bounced()

        # Status 204 on force_set_bounced
        mock_put.return_value = MagicMock(status_code=204)
        self.partner.brevo_force_set_bounced()
        self.assertTrue(self.partner.email_bounced)

        # Status 500 on force_set_bounced
        self.partner.email_bounced = False
        mock_put.return_value = MagicMock(status_code=500)
        self.partner.brevo_force_set_bounced()
        self.assertFalse(self.partner.email_bounced)

        # Status 204 on force_unset_bounced
        self.partner.email_bounced = True
        mock_put.return_value = MagicMock(status_code=204)
        self.partner.brevo_force_unset_bounced()
        self.assertFalse(self.partner.email_bounced)

        # Status 404 on force_unset_bounced
        self.partner.email_bounced = True
        mock_put.return_value = MagicMock(status_code=404)
        self.partner.brevo_force_unset_bounced()
        self.assertFalse(self.partner.email_bounced)

        # Status 500 on force_unset_bounced
        self.partner.email_bounced = True
        mock_put.return_value = MagicMock(status_code=500)
        self.partner.brevo_force_unset_bounced()
        self.assertTrue(self.partner.email_bounced)

    def test_partner_email_bounced_set(self):
        partner_no_email = self.env["res.partner"].create(
            {"name": "No Email Partner", "email": False}
        )
        partner_no_email.email_bounced_set(self.tracking_email, "Test reason")

        event = self.env["mail.tracking.event"].create(
            {
                "tracking_email_id": self.tracking_email.id,
                "event_type": "hard_bounce",
            }
        )
        self.partner.sudo().email_bounced_set(
            self.tracking_email, "Mailbox does not exist", event=event
        )
        messages = self.partner.message_ids
        self.assertTrue(messages)
        self.assertIn("Email has been bounced", messages[0].body)
        self.assertIn("Mailbox does not exist", messages[0].body)

        self.partner.with_user(SUPERUSER_ID).email_bounced_set(
            self.tracking_email, "No event reason", event=None
        )
        self.assertIn("unknown", self.partner.message_ids[0].body)

        # Non-superuser call (self.env.su is False, branch 40->42)
        non_su_user = self.env["res.users"].create(
            {
                "name": "Non SU User",
                "login": "non_su_user_brevo",
                "email": "nonsu@example.com",
            }
        )
        self.partner.with_user(non_su_user).email_bounced_set(
            self.tracking_email, "Non SU test reason", event=event
        )

    def test_res_config_settings_get_values(self):
        self.icp.set_param("brevo.webhooks_registered", False)
        wizard = self.env["res.config.settings"].create({})
        values = wizard.get_values()
        self.assertTrue(values.get("mail_tracking_brevo_enabled"))
        self.assertFalse(values.get("mail_tracking_brevo_webhooks_registered"))

        self.icp.set_param("brevo.webhooks_registered", True)
        values = wizard.get_values()
        self.assertTrue(values.get("mail_tracking_brevo_webhooks_registered"))
        self.icp.set_param("brevo.webhooks_registered", False)

    @patch("requests.post")
    @patch("requests.get")
    @patch("requests.delete")
    def test_res_config_settings_webhooks(self, mock_del, mock_get, mock_post):
        wizard = self.env["res.config.settings"].create({})

        mock_post.return_value = MagicMock(status_code=201)
        wizard.mail_tracking_brevo_register_webhooks()
        mock_post.assert_called_once()

        # Webhook registration without webhook_token (branch 86->88)
        self.icp.set_param("brevo.webhook_token", False)
        wizard.mail_tracking_brevo_register_webhooks()
        self.icp.set_param("brevo.webhook_token", "test-webhook-token-67890")

        mock_post_err = MagicMock()
        mock_post_err.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_post_err.text = "Error detail"
        mock_post.return_value = mock_post_err
        with (
            mute_logger("odoo.addons.mail_tracking_brevo.wizards.res_config_settings"),
            self.assertRaises(UserError),
        ):
            wizard.mail_tracking_brevo_register_webhooks()

        mock_post_err.text = ""
        with (
            mute_logger("odoo.addons.mail_tracking_brevo.wizards.res_config_settings"),
            self.assertRaises(UserError),
        ):
            wizard.mail_tracking_brevo_register_webhooks()

        target_url = (
            f"http://localhost:8069/mail/tracking/brevo/all?db={self.env.cr.dbname}"
        )
        mock_get_res = MagicMock(status_code=200)
        mock_get_res.json.return_value = {
            "webhooks": [
                {"id": 12, "url": target_url},
                {"id": 99, "url": "https://other-domain.com/webhook"},
            ]
        }
        mock_get.return_value = mock_get_res
        mock_del.return_value = MagicMock(status_code=204)

        wizard.mail_tracking_brevo_unregister_webhooks()
        mock_del.assert_called_once()

        mock_get_err = MagicMock()
        mock_get_err.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_get_err.text = "Listing error"
        mock_get.return_value = mock_get_err
        with (
            mute_logger("odoo.addons.mail_tracking_brevo.wizards.res_config_settings"),
            self.assertRaises(UserError),
        ):
            wizard.mail_tracking_brevo_unregister_webhooks()

        mock_get.return_value = mock_get_res
        mock_del_err = MagicMock()
        mock_del_err.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_del_err.text = "Delete error"
        mock_del.return_value = mock_del_err
        with (
            mute_logger("odoo.addons.mail_tracking_brevo.wizards.res_config_settings"),
            self.assertRaises(UserError),
        ):
            wizard.mail_tracking_brevo_unregister_webhooks()

    @patch("odoo.addons.mail_tracking_brevo.controllers.main.ensure_db")
    def test_brevo_controller_webhook(self, mock_ensure_db):
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

        self.icp.set_param("brevo.webhook_token", False)
        with MockRequest(self.env) as request:
            request.get_json_data = lambda: payload
            request.params = {"db": self.env.cr.dbname}
            request.make_response = lambda text, headers: text
            res = self.controller.mail_tracking_brevo_webhook()
            self.assertIn("OK", str(res))
        self.icp.set_param("brevo.webhook_token", "test-webhook-token-67890")

        with MockRequest(self.env) as request:
            request.params = {"db": self.env.cr.dbname, "token": "wrong_token"}
            with (
                mute_logger("odoo.addons.mail_tracking_brevo.controllers.main"),
                self.assertRaises(NotAcceptable),
            ):
                self.controller.mail_tracking_brevo_webhook(token="wrong_token")

        with MockRequest(self.env) as request:
            request.get_json_data = MagicMock(side_effect=ValueError("Malformed JSON"))
            request.params = {
                "db": self.env.cr.dbname,
                "token": "test-webhook-token-67890",
            }
            request.make_response = lambda text, headers: text
            res = self.controller.mail_tracking_brevo_webhook(
                token="test-webhook-token-67890"
            )
            self.assertIn("OK", str(res))

        with MockRequest(self.env) as request:
            request.get_json_data = lambda: {}
            request.params = {
                "db": self.env.cr.dbname,
                "token": "test-webhook-token-67890",
            }
            request.make_response = lambda text, headers: text
            res = self.controller.mail_tracking_brevo_webhook(
                token="test-webhook-token-67890"
            )
            self.assertIn("OK", str(res))

        events_list = [
            "non_dict_event",
            {
                "event": "delivered",
                "email": "brevo_test@example.com",
                "message-id": "<1234567890@test.com>",
                "ts_event": 1725278900,
            },
        ]
        with MockRequest(self.env) as request:
            request.get_json_data = lambda: events_list
            request.params = {
                "db": self.env.cr.dbname,
                "token": "test-webhook-token-67890",
            }
            request.make_response = lambda text, headers: text
            res = self.controller.mail_tracking_brevo_webhook(
                token="test-webhook-token-67890"
            )
            self.assertIn("OK", str(res))

        # Non-dict non-list JSON payload (branch 64->67)
        with MockRequest(self.env) as request:
            request.get_json_data = lambda: "non_dict_payload"
            request.params = {
                "db": self.env.cr.dbname,
                "token": "test-webhook-token-67890",
            }
            request.make_response = lambda text, headers: text
            res = self.controller.mail_tracking_brevo_webhook(
                token="test-webhook-token-67890"
            )
            self.assertIn("OK", str(res))

        # Token only in kwargs, not in request.params
        with MockRequest(self.env) as request:
            request.get_json_data = lambda: payload
            request.params = {"db": self.env.cr.dbname}
            request.make_response = lambda text, headers: text
            res = self.controller.mail_tracking_brevo_webhook(
                token="test-webhook-token-67890"
            )
            self.assertIn("OK", str(res))

        # Token in neither request.params nor kwargs
        with MockRequest(self.env) as request:
            request.params = {"db": self.env.cr.dbname}
            with (
                mute_logger("odoo.addons.mail_tracking_brevo.controllers.main"),
                self.assertRaises(NotAcceptable),
            ):
                self.controller.mail_tracking_brevo_webhook()
