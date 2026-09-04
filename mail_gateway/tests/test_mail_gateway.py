# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
from unittest.mock import MagicMock, patch

from odoo.http import _request_stack
from odoo.tests import tagged

from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail_gateway.controllers.gateway import GatewayController

from .common import MailGatewayTestCase

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestMailGateway(MailGatewayTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gateway = cls.env["mail.gateway"].create(
            {
                "name": "Test Gateway",
                "token": "test-token-001",
                "gateway_type": cls.GATEWAY_TYPE,
                "webhook_key": "test-wh-key-001",
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "GW Test Partner"})
        # A plain internal user that is NOT in the gateway group (and is not the
        # superuser), used to exercise the non-gateway-user code paths.
        cls.basic_user = cls.env["res.users"].create(
            {
                "name": "Basic User",
                "login": "basic_gw_user",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

    # ── mail.gateway ──────────────────────────────────────────────────────────

    def test_gateway_create_and_info(self):
        self.assertEqual(self.gateway.name, "Test Gateway")
        self.assertEqual(self.gateway.gateway_type, self.GATEWAY_TYPE)
        info = self.gateway.gateway_info()
        self.assertEqual(len(info), 1)
        self.assertEqual(info[0]["id"], self.gateway.id)
        self.assertEqual(info[0]["type"], self.GATEWAY_TYPE)
        self.assertEqual(info[0]["name"], "Test Gateway")

    def test_webhook_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        self.assertEqual(
            self.gateway.webhook_url,
            f"{base_url}/gateway/{self.GATEWAY_TYPE}/test-wh-key-001/update",
        )

    def test_can_set_webhook_with_key(self):
        self.assertTrue(self.gateway.can_set_webhook)

    def test_can_set_webhook_without_key(self):
        gw = self.env["mail.gateway"].create(
            {
                "name": "No Key",
                "token": "token-no-key",
                "gateway_type": self.GATEWAY_TYPE,
            }
        )
        self.assertFalse(gw.can_set_webhook)

    def test_set_webhook(self):
        self.gateway.set_webhook()
        self.assertEqual(self.gateway.integrated_webhook_state, "integrated")

    def test_remove_webhook(self):
        self.gateway.integrated_webhook_state = "integrated"
        self.gateway.remove_webhook()
        self.assertFalse(self.gateway.integrated_webhook_state)

    def test_update_webhook(self):
        self.gateway.integrated_webhook_state = "integrated"
        self.gateway.update_webhook()
        self.assertEqual(self.gateway.integrated_webhook_state, "integrated")

    def test_get_gateway_map_integrated(self):
        self.gateway.integrated_webhook_state = "integrated"
        gateway_map = self.env["mail.gateway"]._get_gateway_map(
            state="integrated", gateway_type=self.GATEWAY_TYPE
        )
        self.assertIn("test-wh-key-001", gateway_map)
        self.assertEqual(gateway_map["test-wh-key-001"]["id"], self.gateway.id)

    def test_get_gateway_found(self):
        self.gateway.integrated_webhook_state = "integrated"
        result = self.env["mail.gateway"]._get_gateway(
            "test-wh-key-001", state="integrated", gateway_type=self.GATEWAY_TYPE
        )
        self.assertEqual(result["id"], self.gateway.id)

    def test_get_gateway_not_found(self):
        self.assertFalse(
            self.env["mail.gateway"]._get_gateway(
                "nonexistent-key", state="integrated", gateway_type=self.GATEWAY_TYPE
            )
        )

    def test_get_gateway_empty_key(self):
        self.assertFalse(
            self.env["mail.gateway"]._get_gateway(
                "", state="integrated", gateway_type=self.GATEWAY_TYPE
            )
        )

    # ── mail.gateway.abstract / channel management ────────────────────────────

    def test_get_channel_id_not_found(self):
        self.assertFalse(self.gateway._get_channel_id("nonexistent"))

    def test_get_channel_creates_channel(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "tok-1", {}, force_create=True)
        self.assertTrue(channel)
        self.assertEqual(channel.channel_type, "gateway")
        self.assertEqual(channel.gateway_channel_token, "tok-1")
        self.assertEqual(channel.gateway_id, self.gateway)

    def test_get_channel_returns_existing(self):
        impl = self.env["mail.gateway.abstract"]
        ch1 = impl._get_channel(self.gateway, "tok-2", {}, force_create=True)
        ch2 = impl._get_channel(self.gateway, "tok-2", {})
        self.assertEqual(ch1.id, ch2.id)

    def test_get_channel_security_blocks_auto_create(self):
        self.gateway.has_new_channel_security = True
        impl = self.env["mail.gateway.abstract"]
        self.assertFalse(impl._get_channel(self.gateway, "blocked-tok", {}))
        self.gateway.has_new_channel_security = False

    def test_get_channel_security_allows_force_create(self):
        self.gateway.has_new_channel_security = True
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "force-tok", {}, force_create=True)
        self.assertTrue(channel)
        self.gateway.has_new_channel_security = False

    # ── discuss.channel gateway extension ─────────────────────────────────────

    def test_message_post_creates_gateway_notification(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "post-tok-1", {}, force_create=True)
        msg = channel.message_post(body="Hello Gateway", message_type="comment")
        gw_notifs = msg.notification_ids.filtered(
            lambda n: n.notification_type == "gateway"
        )
        self.assertTrue(gw_notifs)
        self.assertEqual(gw_notifs[0].gateway_channel_id, channel)
        self.assertEqual(gw_notifs[0].gateway_type, self.GATEWAY_TYPE)

    def test_message_post_no_notification_for_notification_type(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "post-tok-2", {}, force_create=True)
        msg = channel.message_post(body="System note", message_type="notification")
        gw_notifs = msg.notification_ids.filtered(
            lambda n: n.notification_type == "gateway"
        )
        self.assertFalse(gw_notifs)

    def test_message_post_no_notification_with_context(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "post-tok-3", {}, force_create=True)
        msg = channel.with_context(no_gateway_notification=True).message_post(
            body="Suppressed", message_type="comment"
        )
        gw_notifs = msg.notification_ids.filtered(
            lambda n: n.notification_type == "gateway"
        )
        self.assertFalse(gw_notifs)

    # ── mail.notification gateway extension ───────────────────────────────────

    def test_set_read_gateway(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "read-tok", {}, force_create=True)
        msg = channel.message_post(body="Unread", message_type="comment")
        notif = msg.notification_ids.filtered(
            lambda n: n.notification_type == "gateway"
        )
        self.assertFalse(notif.is_read)
        notif._set_read_gateway()
        self.assertTrue(notif.is_read)

    def test_post_process_message(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "proc-tok", {}, force_create=True)
        msg = channel.message_post(body="Process test", message_type="comment")
        notif = msg.notification_ids.filtered(
            lambda n: n.notification_type == "gateway"
        )
        self.assertFalse(notif.is_read)
        impl._post_process_message(msg, channel)
        self.assertTrue(notif.is_read)

    # ── res.partner.gateway.channel ───────────────────────────────────────────

    def test_partner_gateway_channel_mail_format(self):
        gw_channel = self.env["res.partner.gateway.channel"].create(
            {
                "partner_id": self.partner.id,
                "gateway_id": self.gateway.id,
                "gateway_token": "partner-tok",
            }
        )
        fmt = gw_channel._mail_format()
        self.assertEqual(fmt["id"], gw_channel.id)
        self.assertEqual(fmt["gateway"]["id"], self.gateway.id)
        self.assertEqual(fmt["gateway"]["type"], self.GATEWAY_TYPE)
        self.assertEqual(len(gw_channel.mail_format()), 1)

    def test_partner_gateway_channel_display_name_with_context(self):
        gw_channel = self.env["res.partner.gateway.channel"].create(
            {
                "partner_id": self.partner.id,
                "gateway_id": self.gateway.id,
                "gateway_token": "display-tok",
            }
        )
        display_name = gw_channel.with_context(
            mail_gateway_partner_info=True
        ).display_name
        self.assertIn(self.partner.display_name, display_name)

    # ── mail.message gateway extension ────────────────────────────────────────

    def test_gateway_thread_data_empty_without_link(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "thread-tok-1", {}, force_create=True)
        msg = channel.message_post(body="Thread data test", message_type="comment")
        # fields.Json stores empty dict as False in Odoo 19
        self.assertFalse(msg.gateway_thread_data)

    def test_send_to_gateway_thread(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(
            self.gateway, "send-thread-tok", {}, force_create=True
        )
        gw_channel = self.env["res.partner.gateway.channel"].create(
            {
                "partner_id": self.partner.id,
                "gateway_id": self.gateway.id,
                "gateway_token": "send-thread-tok",
            }
        )
        orig_msg = channel.message_post(body="Original", message_type="comment")
        orig_msg._send_to_gateway_thread(gw_channel)
        child_msgs = channel.message_ids.filtered(
            lambda m: m.gateway_message_id == orig_msg
        )
        self.assertTrue(child_msgs)

    # ── mail.message.gateway.link wizard ──────────────────────────────────────

    def test_gateway_link_wizard(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "link-tok", {}, force_create=True)
        msg = channel.message_post(body="Link me", message_type="comment")
        target = self.env["res.partner"].create({"name": "Link Target"})
        wizard = self.env["mail.message.gateway.link"].create(
            {
                "message_id": msg.id,
                "resource_ref": f"res.partner,{target.id}",
            }
        )
        wizard.link_message()
        self.assertTrue(msg.gateway_message_id)
        self.assertEqual(msg.gateway_message_id.model, "res.partner")
        self.assertEqual(msg.gateway_thread_data["model"], "res.partner")

    # ── mail.guest.manage wizard ───────────────────────────────────────────────

    def test_guest_manage_create_partner(self):
        guest = self.env["mail.guest"].create(
            {
                "name": "Test Guest",
                "gateway_id": self.gateway.id,
                "gateway_token": "guest-create-tok",
            }
        )
        self.env["mail.guest.manage"].create({"guest_id": guest.id}).create_partner()
        gw_channel = self.env["res.partner.gateway.channel"].search(
            [
                ("gateway_id", "=", self.gateway.id),
                ("gateway_token", "=", "guest-create-tok"),
            ]
        )
        self.assertTrue(gw_channel)

    def test_guest_manage_merge_partner(self):
        guest = self.env["mail.guest"].create(
            {
                "name": "Merge Guest",
                "gateway_id": self.gateway.id,
                "gateway_token": "guest-merge-tok",
            }
        )
        target = self.env["res.partner"].create({"name": "Merge Target"})
        wizard = self.env["mail.guest.manage"].create(
            {"guest_id": guest.id, "partner_id": target.id}
        )
        wizard.merge_partner()
        gw_channel = self.env["res.partner.gateway.channel"].search(
            [
                ("partner_id", "=", target.id),
                ("gateway_id", "=", self.gateway.id),
            ]
        )
        self.assertTrue(gw_channel)

    # ── mail.message.gateway.send wizard ──────────────────────────────────────

    def test_gateway_send_wizard(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "send-wiz-tok", {}, force_create=True)
        gw_channel = self.env["res.partner.gateway.channel"].create(
            {
                "partner_id": self.partner.id,
                "gateway_id": self.gateway.id,
                "gateway_token": "send-wiz-tok",
            }
        )
        msg = channel.message_post(body="Send via wizard", message_type="comment")
        wizard = self.env["mail.message.gateway.send"].create(
            {
                "message_id": msg.id,
                "partner_id": self.partner.id,
                "gateway_channel_id": gw_channel.id,
            }
        )
        wizard.send()
        child_msgs = channel.message_ids.filtered(lambda m: m.gateway_message_id == msg)
        self.assertTrue(child_msgs)

    # ── mail.compose.gateway.message wizard ───────────────────────────────────

    def test_compose_gateway_message_static_values(self):
        impl = self.env["mail.gateway.abstract"]
        impl._get_channel(self.gateway, "compose-tok", {}, force_create=True)
        gw_channel = self.env["res.partner.gateway.channel"].create(
            {
                "partner_id": self.partner.id,
                "gateway_id": self.gateway.id,
                "gateway_token": "compose-tok",
            }
        )
        wizard = self.env["mail.compose.gateway.message"].create(
            {
                "model": "res.partner",
                "res_ids": [self.partner.id],
                "body": "<p>Hello</p>",
                "wizard_channel_ids": [gw_channel.id],
            }
        )
        values = wizard._prepare_mail_values_static()
        self.assertIn("gateway_notifications", values)
        self.assertEqual(len(values["gateway_notifications"]), 1)
        self.assertEqual(
            values["gateway_notifications"][0]["gateway_channel_id"], gw_channel.id
        )

    def test_compose_gateway_message_dynamic_values(self):
        impl = self.env["mail.gateway.abstract"]
        impl._get_channel(self.gateway, "compose-dyn-tok", {}, force_create=True)
        gw_channel = self.env["res.partner.gateway.channel"].create(
            {
                "partner_id": self.partner.id,
                "gateway_id": self.gateway.id,
                "gateway_token": "compose-dyn-tok",
            }
        )
        wizard = self.env["mail.compose.gateway.message"].create(
            {
                "model": "res.partner",
                "res_ids": [self.partner.id],
                "body": "<p>Dynamic</p>",
                "wizard_channel_ids": [gw_channel.id],
            }
        )
        values = wizard._prepare_mail_values_dynamic([self.partner.id])
        self.assertIn("gateway_notifications", values[self.partner.id])

    # ── res.users / res.users.settings ────────────────────────────────────────

    def test_user_gateway_ids(self):
        user = self.env["res.users"].browse(self.env.uid)
        user.gateway_ids = [self.gateway.id]
        self.assertIn(self.gateway, user.gateway_ids)

    def test_users_settings_gateway_category_field(self):
        settings = self.env["res.users.settings"]._find_or_create_for_user(
            self.env.user
        )
        self.assertTrue(settings.is_discuss_sidebar_category_gateway_open)
        settings.is_discuss_sidebar_category_gateway_open = False
        self.assertFalse(settings.is_discuss_sidebar_category_gateway_open)

    # ── mail.thread extensions ─────────────────────────────────────────────────

    def test_get_message_create_valid_field_names(self):
        field_names = self.env["mail.thread"]._get_message_create_valid_field_names()
        self.assertIn("gateway_type", field_names)
        self.assertIn("gateway_notifications", field_names)

    def test_get_allowed_message_post_params(self):
        params = self.env["mail.thread"]._get_allowed_message_post_params()
        self.assertIn("gateway_notifications", params)

    def test_notify_get_recipients_with_gateway_notifications(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "notify-tok", {}, force_create=True)
        gw_channel = self.env["res.partner.gateway.channel"].create(
            {
                "partner_id": self.partner.id,
                "gateway_id": self.gateway.id,
                "gateway_token": "notify-tok",
            }
        )
        msg = channel.message_post(body="Notify test", message_type="comment")
        gateway_notifications = [
            {
                "partner_id": self.partner.id,
                "channel_type": "gateway",
                "gateway_channel_id": gw_channel.id,
            }
        ]
        recipients = self.env["mail.thread"]._notify_get_recipients(
            msg, {}, gateway_notifications=gateway_notifications
        )
        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0]["notif"], "gateway")
        self.assertEqual(recipients[0]["gateway_channel_id"], gw_channel.id)

    def test_notify_get_recipients_with_link_context(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "link-ctx-tok", {}, force_create=True)
        msg = channel.message_post(body="Link context", message_type="comment")
        recipients = (
            self.env["mail.thread"]
            .with_context(link_gateway_message=True)
            ._notify_get_recipients(msg, {})
        )
        self.assertEqual(recipients, [])

    # ── hooks ─────────────────────────────────────────────────────────────────

    def test_pre_init_hook_is_idempotent(self):
        from ..hooks import pre_init_hook

        pre_init_hook(self.env)

    # ── discuss.channel additional coverage ───────────────────────────────────

    def test_generate_avatar_gateway_returns_false(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "avatar-tok", {}, force_create=True)
        self.assertFalse(channel._generate_avatar_gateway())
        self.assertFalse(channel._generate_avatar())

    def test_generate_avatar_non_gateway_uses_super(self):
        channel = self.env["discuss.channel"].create({"name": "Regular"})
        channel._generate_avatar()  # delegates to super()

    def test_discuss_channel_to_store(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "ch-store-tok", {}, force_create=True)
        store = Store()
        channel._to_store(
            store,
            ["gateway_id", "gateway_token", "gateway_message_ids", "channel_type"],
        )

    # ── mail.thread additional coverage ───────────────────────────────────────

    def test_get_notify_valid_parameters(self):
        params = self.env["mail.thread"]._get_notify_valid_parameters()
        self.assertIn("gateway_notifications", params)

    def test_notify_thread_by_gateway_valid_and_invalid(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(
            self.gateway, "gw-direct-tok", {}, force_create=True
        )
        gw_channel = self.env["res.partner.gateway.channel"].create(
            {
                "partner_id": self.partner.id,
                "gateway_id": self.gateway.id,
                "gateway_token": "gw-direct-tok",
            }
        )
        msg = channel.message_post(body="Test", message_type="comment")
        thread = self.env["mail.thread"]
        # Valid: calls _send_to_gateway_thread
        thread._notify_thread_by_gateway(
            msg, [{"notif": "gateway", "gateway_channel_id": gw_channel.id}]
        )
        # Invalid: no gateway_channel_id → skipped
        thread._notify_thread_by_gateway(
            msg, [{"notif": "gateway", "gateway_channel_id": False}]
        )
        # Invalid: wrong notif type → skipped
        thread._notify_thread_by_gateway(
            msg, [{"notif": "email", "gateway_channel_id": gw_channel.id}]
        )

    def test_thread_to_store_no_followers(self):
        target = self.env["res.partner"].create({"name": "No-Follower"})
        store = Store()
        target._thread_to_store(store, [], request_list=["x"])

    def test_thread_to_store_with_gateway_followers(self):
        self.env["res.partner.gateway.channel"].create(
            {
                "partner_id": self.partner.id,
                "gateway_id": self.gateway.id,
                "gateway_token": "thread-store-tok",
            }
        )
        target = self.env["res.partner"].create({"name": "Thread Target"})
        target.message_subscribe(self.partner.ids)
        store = Store()
        target._thread_to_store(store, [], request_list=["x"])

    def test_check_can_update_message_content_non_channel(self):
        msg = self.partner.message_post(body="Non-channel msg", message_type="comment")
        # On a non-discuss.channel thread, messages without gateway_message_ids pass
        try:
            self.partner._check_can_update_message_content(msg)
        except Exception as err:
            _logger.info("Expected access-right error: %s", err)

    def test_message_update_content_empty_body_unlinks_gateway(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "unlink-tok", {}, force_create=True)
        orig_msg = channel.message_post(body="Original", message_type="comment")
        # Create a child message pointing to orig_msg
        partner_msg = self.partner.message_post(body="Child", message_type="comment")
        partner_msg.gateway_message_id = orig_msg
        self.assertTrue(orig_msg.gateway_message_ids)
        # Updating orig_msg with empty body should unlink partner_msg
        channel._message_update_content(orig_msg, body="")
        self.assertFalse(partner_msg.gateway_message_id)

    # ── tools/discuss.py coverage ─────────────────────────────────────────────

    def test_extended_get_id_adds_gateway_channels(self):
        gw_channel = self.env["res.partner.gateway.channel"].create(
            {
                "partner_id": self.partner.id,
                "gateway_id": self.gateway.id,
                "gateway_token": "ext-get-id-tok",
            }
        )
        store_one = Store.One(self.partner)
        result = Store.One._get_id(store_one)
        if isinstance(result, dict):
            self.assertIn("gateway_channels", result)
            channel_ids = [c["id"] for c in result["gateway_channels"]]
            self.assertIn(gw_channel.id, channel_ids)

    # ── res.users._init_messaging ─────────────────────────────────────────────

    def test_init_messaging(self):
        self.env.user.gateway_ids = [self.gateway.id]
        store = Store()
        self.env.user._init_messaging(store)

    # ── gateway_user group-gated paths ────────────────────────────────────────

    def test_compute_gateway_channel_ids_gateway_user_group(self):
        gateway_group = self.env.ref("mail_gateway.gateway_user")
        gateway_group.user_ids |= self.env.user
        try:
            impl = self.env["mail.gateway.abstract"]
            channel = impl._get_channel(
                self.gateway, "gc-grp-tok", {}, force_create=True
            )
            msg = channel.message_post(body="GC group test", message_type="comment")
            _ = msg.gateway_channel_ids
            _ = msg.gateway_channel_data
        finally:
            gateway_group.user_ids -= self.env.user

    def test_build_bus_channel_list_gateway_user(self):
        gateway_group = self.env.ref("mail_gateway.gateway_user")
        gateway_group.user_ids |= self.env.user
        impl = self.env["mail.gateway.abstract"]
        impl._get_channel(self.gateway, "ws-bus-tok", {}, force_create=True)
        mock_req = MagicMock()
        mock_req.session.uid = self.env.uid
        mock_req.env = self.env
        # Bind the request on the stack so the `request` proxy resolves in
        # every `_build_bus_channel_list` override (bus reads it too).
        _request_stack.push(mock_req)
        try:
            result = self.env["ir.websocket"]._build_bus_channel_list([])
            self.assertTrue(
                any(getattr(c, "channel_type", None) == "gateway" for c in result)
            )
        finally:
            _request_stack.pop()
            gateway_group.user_ids -= self.env.user

    # ── mail.notification.send_gateway failure path ───────────────────────────

    def test_send_gateway_failure_type_notifies(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(
            self.gateway, "fail-notify-tok", {}, force_create=True
        )
        msg = channel.message_post(body="Fail test", message_type="comment")
        notif = self.env["mail.notification"].create(
            {
                "mail_message_id": msg.id,
                "gateway_channel_id": channel.id,
                "notification_type": "gateway",
                "gateway_type": self.GATEWAY_TYPE,
                "failure_type": "unknown",
            }
        )
        # _send is mocked to return None; failure_type stays "unknown",
        # triggering _notify_message_notification_update
        notif.send_gateway()

    # ── discuss.channel._message_update_content gateway hook ─────────────────

    def test_discuss_channel_message_update_content_gateway_hook(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "uc-hook-tok", {}, force_create=True)
        msg = channel.message_post(body="Original", message_type="comment")
        # gateway_notification_ids are present → _update_content_after_hook is called
        channel._message_update_content(msg, body="Updated body")

    # ── mail.thread._notify_thread_by_email gateway recipients ───────────────

    def test_notify_thread_by_email_with_gateway_recipients(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "email-gw-tok", {}, force_create=True)
        gw_channel = self.env["res.partner.gateway.channel"].create(
            {
                "partner_id": self.partner.id,
                "gateway_id": self.gateway.id,
                "gateway_token": "email-gw-tok",
            }
        )
        msg = channel.message_post(body="Email GW", message_type="comment")
        self.env["mail.thread"]._notify_thread_by_email(
            msg,
            [{"notif": "gateway", "gateway_channel_id": gw_channel.id}],
        )

    def test_notify_thread_by_email_without_gateway_recipients(self):
        # No gateway recipient -> _notify_thread_by_gateway is skipped.
        msg = self.partner.message_post(body="Plain email", message_type="comment")
        self.env["mail.thread"]._notify_thread_by_email(msg, [])

    # ── mail.gateway.set_webhook guard ────────────────────────────────────────

    def test_set_webhook_without_key_is_noop(self):
        gw = self.env["mail.gateway"].create(
            {
                "name": "No Key Webhook",
                "token": "token-no-key-wh",
                "gateway_type": self.GATEWAY_TYPE,
            }
        )
        self.assertFalse(gw.can_set_webhook)
        gw.set_webhook()
        self.assertFalse(gw.integrated_webhook_state)

    # ── mail.gateway.abstract additional coverage ─────────────────────────────

    def test_post_process_reply_is_noop(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "reply-tok", {}, force_create=True)
        msg = channel.message_post(body="Reply base", message_type="comment")
        # Base implementation is a no-op; just make sure it is callable.
        self.assertIsNone(impl._post_process_reply(msg))

    def test_get_message_body(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "body-tok", {}, force_create=True)
        msg = channel.message_post(body="<p>Body content</p>", message_type="comment")
        notif = msg.notification_ids.filtered(
            lambda n: n.notification_type == "gateway"
        )
        self.assertEqual(impl._get_message_body(notif), msg.body)

    def test_get_channel_vals_with_author(self):
        impl = self.env["mail.gateway.abstract"]
        impl_cls = type(impl)
        with patch.object(impl_cls, "_get_author", return_value=self.partner):
            vals = impl._get_channel_vals(self.gateway, "author-tok", {})
        # The author is added as a channel member and used as the channel name.
        self.assertEqual(vals["name"], self.partner.name)
        member_partners = [
            command[2].get("partner_id") for command in vals["channel_member_ids"]
        ]
        self.assertIn(self.partner.id, member_partners)

    def test_send_raises_not_implemented(self):
        # The class-level patch in common.py only shadows the registry leaf class,
        # so the original abstract implementation still raises NotImplementedError.
        from ..models.mail_gateway_abstract import (
            MailGatewayAbstract,
        )

        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "raise-tok", {}, force_create=True)
        msg = channel.message_post(body="Raise", message_type="comment")
        notif = msg.notification_ids.filtered(
            lambda n: n.notification_type == "gateway"
        )
        with self.assertRaises(NotImplementedError):
            MailGatewayAbstract._send(impl, self.gateway, notif)

    # ── mail.guest._to_store_defaults ─────────────────────────────────────────

    def test_guest_to_store_defaults(self):
        guest = self.env["mail.guest"].create(
            {
                "name": "Store Guest",
                "gateway_id": self.gateway.id,
                "gateway_token": "guest-store-tok",
            }
        )
        store = Store()
        store.add(guest)
        self.assertTrue(store.get_result())

    # ── discuss.channel additional branches ───────────────────────────────────

    def test_generate_avatar_gateway_with_avatar(self):
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(self.gateway, "avatar2-tok", {}, force_create=True)
        channel_cls = type(channel)
        with patch.object(
            channel_cls, "_generate_avatar_gateway", return_value="raw-avatar"
        ):
            self.assertTrue(channel._generate_avatar())

    def test_message_update_content_non_gateway_channel(self):
        # channel_type != "gateway" → the gateway update hook is skipped.
        channel = self.env["discuss.channel"].create(
            {"name": "Regular Update", "channel_type": "channel"}
        )
        msg = channel.message_post(body="Regular", message_type="comment")
        channel._message_update_content(msg, body="Updated regular")

    # ── ir.websocket bus channel branches ─────────────────────────────────────

    def test_build_bus_channel_list_no_session(self):
        mock_req = MagicMock()
        mock_req.session.uid = False
        mock_req.env = self.env
        _request_stack.push(mock_req)
        try:
            result = self.env["ir.websocket"]._build_bus_channel_list([])
            self.assertFalse(
                any(getattr(c, "channel_type", None) == "gateway" for c in result)
            )
        finally:
            _request_stack.pop()

    def test_build_bus_channel_list_non_gateway_user(self):
        # Session present but user is not in the gateway group → no gateway channels.
        impl = self.env["mail.gateway.abstract"]
        impl._get_channel(self.gateway, "ws-nogrp-tok", {}, force_create=True)
        basic_env = self.env(user=self.basic_user)
        mock_req = MagicMock()
        mock_req.session.uid = self.basic_user.id
        mock_req.env = basic_env
        _request_stack.push(mock_req)
        try:
            result = basic_env["ir.websocket"]._build_bus_channel_list([])
            self.assertFalse(
                any(getattr(c, "channel_type", None) == "gateway" for c in result)
            )
        finally:
            _request_stack.pop()

    # ── res.partner.gateway.channel display name without context ──────────────

    def test_partner_gateway_channel_display_name_without_context(self):
        gw_channel = self.env["res.partner.gateway.channel"].create(
            {
                "partner_id": self.partner.id,
                "gateway_id": self.gateway.id,
                "gateway_token": "noctx-tok",
            }
        )
        # Without the mail_gateway_partner_info context → standard display name.
        self.assertEqual(gw_channel.display_name, gw_channel.name)

    # ── mail.message._compute_gateway_channel_ids without group ───────────────

    def test_compute_gateway_channel_ids_without_group(self):
        # Computed as a non-gateway user -> the empty-channel else branch is taken.
        msg = self.partner.message_post(body="GC no group", message_type="comment")
        msg_as_basic = msg.with_user(self.basic_user)
        self.assertFalse(msg_as_basic.gateway_channel_ids)
        self.assertEqual(msg_as_basic.gateway_channel_data["channels"], [])

    # ── mail.message._send_to_gateway_thread extra branches ───────────────────

    def test_send_to_gateway_thread_sets_gateway_type(self):
        impl = self.env["mail.gateway.abstract"]
        impl._get_channel(self.gateway, "set-type-tok", {}, force_create=True)
        gw_channel = self.env["res.partner.gateway.channel"].create(
            {
                "partner_id": self.partner.id,
                "gateway_id": self.gateway.id,
                "gateway_token": "set-type-tok",
            }
        )
        # A message posted on a regular thread has no gateway_type yet.
        msg = self.partner.message_post(body="No type yet", message_type="comment")
        self.assertFalse(msg.gateway_type)
        msg._send_to_gateway_thread(gw_channel)
        self.assertEqual(msg.gateway_type, self.gateway.gateway_type)

    def test_send_to_gateway_thread_propagates_failure(self):
        impl = self.env["mail.gateway.abstract"]
        impl_cls = type(impl)
        channel = impl._get_channel(
            self.gateway, "fail-prop-tok", {}, force_create=True
        )
        gw_channel = self.env["res.partner.gateway.channel"].create(
            {
                "partner_id": self.partner.id,
                "gateway_id": self.gateway.id,
                "gateway_token": "fail-prop-tok",
            }
        )
        orig_msg = channel.message_post(body="Original", message_type="comment")

        def _failing_send(_gateway, record, **_kwargs):
            record.write({"failure_type": "unknown", "failure_reason": "boom"})

        # The notification created while sending to the thread fails → its failure
        # details are propagated to the notification linked to the source message.
        with patch.object(impl_cls, "_send", side_effect=_failing_send):
            orig_msg._send_to_gateway_thread(gw_channel)
        propagated = orig_msg.notification_ids.filtered(
            lambda n: n.failure_type == "unknown"
        )
        self.assertTrue(propagated)
        self.assertEqual(propagated[0].failure_reason, "boom")

    # ── mail.thread._notify_get_recipients recipient types ────────────────────

    def test_notify_get_recipients_skips_without_channel_type(self):
        msg = self.partner.message_post(body="No channel type", message_type="comment")
        recipients = self.env["mail.thread"]._notify_get_recipients(
            msg,
            {},
            gateway_notifications=[{"partner_id": self.partner.id}],
        )
        self.assertEqual(recipients, [])

    def test_notify_get_recipients_recipient_types(self):
        # Internal (non-share) user → type "user".
        internal_partner = self.env.user.partner_id
        # Share user → type "portal".
        portal_group = self.env.ref("base.group_portal")
        portal_user = self.env["res.users"].create(
            {
                "name": "Portal GW User",
                "login": "portal_gw_user",
                "group_ids": [(6, 0, [portal_group.id])],
            }
        )
        msg = self.partner.message_post(body="Types", message_type="comment")
        recipients = self.env["mail.thread"]._notify_get_recipients(
            msg,
            {},
            gateway_notifications=[
                {"partner_id": internal_partner.id, "channel_type": "gateway"},
                {"partner_id": portal_user.partner_id.id, "channel_type": "gateway"},
                {"partner_id": self.partner.id, "channel_type": "gateway"},
            ],
        )
        types = {r["id"]: r["type"] for r in recipients}
        self.assertEqual(types[internal_partner.id], "user")
        self.assertEqual(types[portal_user.partner_id.id], "portal")
        self.assertEqual(types[self.partner.id], "customer")

    # ── tools/discuss.py extended_get_id with dict result ─────────────────────

    def test_extended_get_id_with_dict_result(self):
        gw_channel = self.env["res.partner.gateway.channel"].create(
            {
                "partner_id": self.partner.id,
                "gateway_id": self.gateway.id,
                "gateway_token": "ext-dict-tok",
            }
        )
        # as_thread=True makes Store.One._get_id return a dict already.
        store_one = Store.One(self.partner, as_thread=True)
        result = Store.One._get_id(store_one)
        self.assertIsInstance(result, dict)
        self.assertIn("gateway_channels", result)
        channel_ids = [c["id"] for c in result["gateway_channels"]]
        self.assertIn(gw_channel.id, channel_ids)

    # ── mail.guest.manage with existing channel members ───────────────────────

    def test_guest_manage_merge_with_channel_members(self):
        guest = self.env["mail.guest"].create(
            {
                "name": "Member Guest",
                "gateway_id": self.gateway.id,
                "gateway_token": "guest-member-tok",
            }
        )
        impl = self.env["mail.gateway.abstract"]
        channel = impl._get_channel(
            self.gateway, "guest-member-tok", {}, force_create=True
        )
        member = self.env["discuss.channel.member"].create(
            {"channel_id": channel.id, "guest_id": guest.id}
        )
        target = self.env["res.partner"].create({"name": "Member Target"})
        wizard = self.env["mail.guest.manage"].create(
            {"guest_id": guest.id, "partner_id": target.id}
        )
        wizard.merge_partner()
        # The guest member was replaced by a partner member and the channel renamed.
        self.assertFalse(member.exists())
        self.assertEqual(channel.name, target.complete_name)
        partner_member = self.env["discuss.channel.member"].search(
            [("channel_id", "=", channel.id), ("partner_id", "=", target.id)]
        )
        self.assertTrue(partner_member)


@tagged("post_install", "-at_install")
class TestMailGatewayController(MailGatewayTestCase):
    """Test GatewayController using a mocked request to avoid HttpCase cursor issues."""

    _CTRL_MODULE = "odoo.addons.mail_gateway.controllers.gateway"
    _DISCUSS_MODULE = "odoo.addons.mail.tools.discuss"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gateway = cls.env["mail.gateway"].create(
            {
                "name": "Ctrl Gateway",
                "token": "ctrl-token",
                "gateway_type": cls.GATEWAY_TYPE,
                "webhook_key": "ctrl-wh-key",
                "integrated_webhook_state": "integrated",
            }
        )
        cls.controller = GatewayController()

    def _mock_request(self, method="POST", data=b"{}"):
        mock_req = MagicMock()
        mock_req.env = self.env
        mock_req.cookies = {}
        mock_req.httprequest.method = method
        mock_req.httprequest.get_data.return_value = data
        mock_req.httprequest.charset = "utf-8"
        mock_req.make_response.side_effect = lambda body, headers=None: body
        return mock_req

    def _call(self, token, method="POST", data=b"{}"):
        mock_req = self._mock_request(method=method, data=data)
        with (
            patch(f"{self._CTRL_MODULE}.request", mock_req),
            patch(f"{self._DISCUSS_MODULE}.request", mock_req),
            patch(f"{self._DISCUSS_MODULE}.wsrequest", mock_req),
        ):
            self.controller.post_update(self.GATEWAY_TYPE, token)
        return mock_req

    def test_post_unknown_token_returns_empty(self):
        # Unknown token → controller logs a WARNING; suppress it to avoid CI failure.
        with self.assertLogs("odoo.addons.mail_gateway.controllers.gateway", "WARNING"):
            mock_req = self._call("unknown-key")
        self.assertEqual(json.loads(mock_req.make_response.call_args[0][0]), {})

    def test_post_integrated_gateway(self):
        self.env.registry.clear_cache()
        mock_req = self._call("ctrl-wh-key", data=json.dumps({"msg": "hello"}).encode())
        self.assertEqual(json.loads(mock_req.make_response.call_args[0][0]), {})

    def test_get_no_pending_returns_empty(self):
        # Gateway is "integrated", not "pending" — GET returns {}
        mock_req = self._call("ctrl-wh-key", method="GET")
        self.assertEqual(json.loads(mock_req.make_response.call_args[0][0]), {})

    def test_post_unverified_returns_empty(self):
        # _verify_update returns False → controller logs a WARNING and returns {}.
        impl_cls = type(self.env["mail.gateway.abstract"])
        self.env.registry.clear_cache()
        with patch.object(impl_cls, "_verify_update", return_value=False):
            with self.assertLogs(
                "odoo.addons.mail_gateway.controllers.gateway", "WARNING"
            ):
                mock_req = self._call(
                    "ctrl-wh-key", data=json.dumps({"msg": "hi"}).encode()
                )
        self.assertEqual(json.loads(mock_req.make_response.call_args[0][0]), {})

    def test_get_pending_calls_receive_get_update(self):
        gw = self.env["mail.gateway"].create(
            {
                "name": "Pending GW",
                "token": "pending-token",
                "gateway_type": self.GATEWAY_TYPE,
                "webhook_key": "pending-wh-key",
                "integrated_webhook_state": "pending",
            }
        )
        self.env.registry.clear_cache()
        mock_req = self._call("pending-wh-key", method="GET")
        # _receive_get_update returns make_response({}) → called once
        mock_req.make_response.assert_called_once()
        gw.unlink()
