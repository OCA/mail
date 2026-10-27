# Copyright 2022 CreuBlanca
# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json
import time
from unittest.mock import patch

import telegram
from telegram.ext import ExtBot

from odoo.tests.common import HttpCase, new_test_user, tagged
from odoo.tools import file_open, mute_logger

from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail_gateway.tests.common import MailGatewayTestCase


class AttachmentFile:
    def __init__(self, file=False):
        self.file = file

    async def download_as_bytearray(self):
        if not self.file:
            return b"A" * 3138
        return file_open(self.file, mode="rb").read()


def getMyBot(message_id=1234, file=False):
    class MyBot(ExtBot):
        async def get_file(self, file_id, *args, **kwargs):
            return AttachmentFile(file)

        def _validate_token(self, *args, **kwargs):
            return

        async def initialize(self, *args, **kwargs):
            return

        async def setWebhook(self, *args, **kwargs):
            return {}

        async def get_webhook_info(self, *args, **kwargs):
            return telegram.WebhookInfo.de_json(
                {
                    "pending_update_count": 0,
                    "url": False,
                    "has_custom_certificate": False,
                },
                self,
            )

        async def get_chat(self, chat_id, *args, **kwargs):
            return telegram.Chat.de_json(
                {
                    "id": chat_id,
                    "type": "private",
                },
                self,
            )

        async def _send_message(self, endpoint, data, *args, **kwargs):
            return telegram.Message.de_json(
                {
                    "date": int(time.time()),
                    "message_id": message_id,
                    "chat": {
                        "id": data["chat_id"],
                        "type": "private",
                    },
                },
                self,
            )

    return MyBot


@tagged("-at_install", "post_install")
class TestMailGatewayTelegram(MailGatewayTestCase, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.webhook = "demo_hook"
        cls.user = new_test_user(
            cls.env,
            login="gateway_test_user",
            groups="base.group_user,mail_gateway.gateway_user",
        )
        cls.webhook_user = new_test_user(
            cls.env, login="webhook_test_user", groups="base.group_user"
        )
        cls.gateway = cls.env["mail.gateway"].create(
            {
                "name": "gateway",
                "gateway_type": "telegram",
                "token": "token",
                "webhook_user_id": cls.webhook_user.id,
                "member_ids": [(4, cls.user.id)],
            }
        )
        cls.password = "my_new_password"
        cls.gateway_token = "12341234"
        cls.message_01 = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {
                    "id": cls.gateway_token,
                    "is_bot": False,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "language_code": "en",
                },
                "chat": {
                    "id": cls.gateway_token,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "type": "private",
                },
                "date": 1639666351,
                "text": "Hi Friend!",
            },
        }
        cls.message_02 = {
            "update_id": 1,
            "message": {
                "message_id": 2,
                "from": {
                    "id": cls.gateway_token,
                    "is_bot": False,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "language_code": "en",
                },
                "chat": {
                    "id": cls.gateway_token,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "type": "private",
                },
                "entities": [{"type": "bot_command", "offset": 0, "length": 6}],
                "date": 1639666351,
                "text": "/start",
            },
        }
        cls.message_03 = {
            "update_id": 1,
            "message": {
                "message_id": 3,
                "from": {
                    "id": cls.gateway_token,
                    "is_bot": False,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "language_code": "en",
                },
                "chat": {
                    "id": cls.gateway_token,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "type": "private",
                },
                "entities": [{"type": "bot_command", "offset": 0, "length": 6}],
                "date": 1639666351,
                "text": f"/start {cls.password}{cls.password}",
            },
        }
        cls.message_04 = {
            "update_id": 1,
            "message": {
                "message_id": 4,
                "from": {
                    "id": cls.gateway_token,
                    "is_bot": False,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "language_code": "en",
                },
                "chat": {
                    "id": cls.gateway_token,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "type": "private",
                },
                "entities": [{"type": "bot_command", "offset": 0, "length": 6}],
                "date": 1639666351,
                "text": f"/start {cls.password}",
            },
        }
        cls.message_05 = {
            "update_id": 5,
            "message": {
                "message_id": 5,
                "from": {
                    "id": cls.gateway_token,
                    "is_bot": False,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "language_code": "en",
                },
                "chat": {
                    "id": cls.gateway_token,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "type": "private",
                },
                "date": 1639666351,
                "document": {
                    "title": "icon.svg",
                    "file_name": "icon.svg",
                    "mime_type": "image/svg+xml",
                    "file_id": "MY_FILE_ID",
                    "file_unique_id": "MY_FILE_UNIQUe_ID",
                    "file_size": 3138,
                },
            },
        }
        cls.reply_to_message_id = 500
        cls.message_06 = {
            "update_id": 1,
            "message": {
                "message_id": 6,
                "from": {
                    "id": cls.gateway_token,
                    "is_bot": False,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "language_code": "en",
                },
                "chat": {
                    "id": cls.gateway_token,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "type": "private",
                },
                "reply_to_message": {
                    "message_id": cls.reply_to_message_id,
                    "from": {
                        "id": cls.gateway_token,
                        "is_bot": False,
                        "first_name": "Demo",
                        "last_name": "Demo",
                        "language_code": "en",
                    },
                    "chat": {
                        "id": cls.gateway_token,
                        "first_name": "Demo",
                        "last_name": "Demo",
                        "type": "private",
                    },
                    "date": 1639666351,
                },
                "date": 1639666351,
                "text": "What do you want to do?",
            },
        }

        cls.message_07 = {
            "update_id": 7,
            "message": {
                "message_id": 7,
                "from": {
                    "id": cls.gateway_token,
                    "is_bot": False,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "language_code": "en",
                },
                "chat": {
                    "id": cls.gateway_token,
                    "first_name": "Demo",
                    "last_name": "Demo",
                    "type": "private",
                },
                "date": 1639666351,
                "sticker": {
                    "width": 512,
                    "height": 512,
                    "emoji": "����",
                    "set_name": "DrugStore",
                    "is_animated": True,
                    "is_video": False,
                    "type": "regular",
                    "thumbnail": {
                        "file_id": "FILE_ID",
                        "file_unique_id": "FILE_UNIQUE_ID",
                        "file_size": 4662,
                        "width": 128,
                        "height": 128,
                    },
                    "thumb": {
                        "file_id": "FILE_ID",
                        "file_unique_id": "FILE_UNIQUE_ID",
                        "file_size": 4662,
                        "width": 128,
                        "height": 128,
                    },
                    "file_id": "FILE_ID",
                    "file_unique_id": "FILE_UNIQUE_ID",
                    "file_size": 10094,
                },
            },
        }
        cls.partner = cls.env["res.partner"].create({"name": "Demo"})

    def setUp(self):
        super().setUp()
        # Public session, so the webhook requests are routed to the test database
        self.authenticate(None, None)

    def test_webhook_management(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch("telegram.Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertEqual(self.gateway.integrated_webhook_state, "integrated")
        with patch("telegram.Bot", getMyBot()):
            self.gateway.update_webhook()
        self.assertEqual(self.gateway.integrated_webhook_state, "integrated")
        with patch("telegram.Bot", getMyBot()):
            self.gateway.remove_webhook()
        self.assertFalse(self.gateway.integrated_webhook_state)

    def set_message(self, message, webhook, timeout=12):
        self.url_open(
            f"/gateway/{self.gateway.gateway_type}/{webhook}/update",
            data=json.dumps(message),
            headers={"Content-Type": "application/json"},
            timeout=timeout,
            # We need to increase the timeout to avoid the test to fail on sticker....
        ).raise_for_status()

    def test_webhook_unsecure_channel(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch("telegram.Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )

        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_01, self.webhook)
        chat = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertTrue(chat)
        self.assertTrue(chat.message_ids)

    def test_webhook_unsecure_channel_start(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_02, self.webhook)
        chat = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertTrue(chat)
        self.assertFalse(chat.message_ids)
        with patch("telegram.Bot", getMyBot()):
            self.set_message(self.message_01, self.webhook)
        chat.invalidate_recordset()
        self.assertTrue(chat.message_ids)

    def test_webhook_secure_channel(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
        self.gateway.write(
            {"has_new_channel_security": True, "telegram_security_key": self.password}
        )
        self.gateway.flush_recordset()
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_01, self.webhook)
        chat = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(chat)
        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_02, self.webhook)
        chat = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(chat)
        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_03, self.webhook)
        chat = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(chat)
        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_04, self.webhook)
        chat = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertTrue(chat)
        self.assertFalse(chat.message_ids)
        with patch("telegram.Bot", ExtBot):
            self.set_message(self.message_01, self.webhook)
        chat.invalidate_recordset()
        self.assertTrue(chat.message_ids)

    def test_webhook_no_webhook(self):
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with self.assertLogs(level="WARNING"):
            self.set_message(self.message_01, self.webhook + self.webhook)
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )

    def test_post_message(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_02, self.webhook)
        channel = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )
        with patch.object(telegram, "Bot", getMyBot()):
            channel.message_post(
                body="HELLO",
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        self.assertTrue(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )

    def test_post_message_image(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_02, self.webhook)
        channel = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )
        with patch.object(telegram, "Bot", getMyBot()):
            channel.message_post(
                attachments=[("demo.png", b"IMAGE")],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        self.assertTrue(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )

    def test_post_message_error(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_02, self.webhook)
        channel = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )
        with mute_logger(
            "odoo.addons.mail_gateway_telegram.models.mail_gateway_telegram"
        ):
            channel.message_post(
                body="My message",
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        notification = self.env["mail.notification"].search(
            [("gateway_channel_id", "=", channel.id)]
        )
        self.assertTrue(notification)
        self.assertEqual(notification.notification_status, "exception")

    def test_post_message_document(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_02, self.webhook)
        channel = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )
        with patch.object(telegram, "Bot", getMyBot()):
            channel.message_post(
                attachments=[("application/pdf", b"PDF")],
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        self.assertTrue(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )

    def test_webhook_attachment(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch("telegram.Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch("telegram.Bot", getMyBot()):
            self.set_message(self.message_05, self.webhook)
        chat = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertTrue(chat)
        self.assertTrue(chat.message_ids)
        self.assertTrue(chat.message_ids.attachment_ids)

    def test_webhook_sticker(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch("telegram.Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch(
            "telegram.Bot",
            getMyBot(file="addons/mail_gateway_telegram/tests/sticker.tgs"),
        ):
            self.set_message(self.message_07, self.webhook, timeout=30)
        chat = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertTrue(chat)
        self.assertTrue(chat.message_ids)
        self.assertTrue(chat.message_ids.attachment_ids)

    def test_webhook_reply(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch("telegram.Bot", getMyBot()):
            self.gateway.set_webhook()
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_02, self.webhook)

        channel = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )
        # Assign the partner to the channel
        self.env["mail.guest.manage"].create(
            {
                "partner_id": self.partner.id,
                "guest_id": self.env["mail.guest"]
                .search(
                    [
                        ("gateway_token", "=", self.gateway_token),
                        ("gateway_id", "=", self.gateway.id),
                    ]
                )
                .id,
            }
        ).merge_partner()
        self.assertTrue(self.partner.gateway_channel_ids)
        with patch.object(telegram, "Bot", getMyBot(self.reply_to_message_id)):
            new_message = self.partner.message_post(
                body="HELLO",
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
                gateway_notifications=[
                    {
                        "channel_type": "gateway",
                        "gateway_channel_id": self.partner.gateway_channel_ids.id,
                        "partner_id": self.partner.id,
                    }
                ],
            )
        self.assertTrue(new_message.gateway_message_ids)
        self.partner.invalidate_recordset()
        messages = self.partner.message_ids
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_06, self.webhook)
        # The message should be assigned the the partner
        self.partner.invalidate_recordset()
        self.assertTrue(self.partner.message_ids - messages)

    def test_webhook_reply_new_partner(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch("telegram.Bot", getMyBot()):
            self.gateway.set_webhook()
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_02, self.webhook)

        channel = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )
        # Assign the partner to the channel
        partner_action = (
            self.env["mail.guest.manage"]
            .create(
                {
                    "guest_id": self.env["mail.guest"]
                    .search(
                        [
                            ("gateway_token", "=", self.gateway_token),
                            ("gateway_id", "=", self.gateway.id),
                        ]
                    )
                    .id,
                }
            )
            .create_partner()
        )
        partner = self.env[partner_action["res_model"]].browse(partner_action["res_id"])
        self.assertTrue(partner.gateway_channel_ids)
        with patch.object(telegram, "Bot", getMyBot(self.reply_to_message_id)):
            new_message = partner.message_post(
                body="HELLO",
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
                gateway_notifications=[
                    {
                        "channel_type": "gateway",
                        "gateway_channel_id": partner.gateway_channel_ids.id,
                        "partner_id": partner.id,
                    }
                ],
            )
        self.assertTrue(new_message.gateway_message_ids)
        partner.invalidate_recordset()
        messages = partner.message_ids
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_06, self.webhook)
        # The message should be assigned the the partner
        partner.invalidate_recordset()
        self.assertTrue(partner.message_ids - messages)

    def test_link_mail_message(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch("telegram.Bot", getMyBot()):
            self.gateway.set_webhook()
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_01, self.webhook)
        messages = self.partner.message_ids
        channel = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertTrue(channel.message_ids)
        self.env["mail.message.gateway.link"].create(
            {
                "message_id": channel.message_ids.id,
                "resource_ref": f"{self.partner._name},{self.partner.id}",
            }
        ).link_message()
        self.assertTrue(self.partner.message_ids - messages)

    def test_send_mail_message(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch("telegram.Bot", getMyBot()):
            self.gateway.set_webhook()
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_01, self.webhook)

        channel = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )
        # Assign the partner to the channel
        partner_action = (
            self.env["mail.guest.manage"]
            .create(
                {
                    "guest_id": self.env["mail.guest"]
                    .search(
                        [
                            ("gateway_token", "=", self.gateway_token),
                            ("gateway_id", "=", self.gateway.id),
                        ]
                    )
                    .id,
                }
            )
            .create_partner()
        )
        partner = self.env[partner_action["res_model"]].browse(partner_action["res_id"])
        message = partner.message_post(body="HELLO")
        self.assertFalse(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )
        with patch.object(telegram, "Bot", getMyBot()):
            self.env["mail.message.gateway.send"].create(
                {
                    "message_id": message.id,
                    "partner_id": partner.id,
                    "gateway_channel_id": partner.gateway_channel_ids.id,
                }
            ).send()
        self.assertTrue(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )

    def test_channel(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch("telegram.Bot", getMyBot()):
            self.gateway.set_webhook()
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_02, self.webhook)

        channel = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertTrue(channel)
        result = Store().add(channel, "_store_channel_fields")._build_result()
        channel_info = next(
            (item for item in result["discuss.channel"] if item["id"] == channel.id),
            None,
        )
        self.assertIsNotNone(channel_info, "Channel info not found in Store result")
        self.assertEqual(channel_info["gateway_id"], self.gateway.id)
        gateway_info = next(
            item for item in result["mail.gateway"] if item["id"] == self.gateway.id
        )
        self.assertEqual(gateway_info["gateway_type"], "telegram")
        self.assertTrue(channel.avatar_128)

    def test_message_update(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_02, self.webhook)
        channel = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertFalse(
            self.env["mail.notification"].search(
                [("gateway_channel_id", "=", channel.id)]
            )
        )
        with patch.object(telegram, "Bot", getMyBot()):
            message = channel.message_post(
                body="HELLO",
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        with patch.object(telegram, "Bot", getMyBot()):
            channel._message_update_content(message, body="New message")
        self.assertRegex(message.body, ".*New message.*")

    def _get_partner_store_info(self):
        """Gateway channels of the partner as the web client receives them."""
        result = (
            Store().add(self.partner, "_store_gateway_channels_fields")._build_result()
        )
        return next(
            item for item in result["res.partner"] if item["id"] == self.partner.id
        )

    def test_messaging(self):
        self.gateway.webhook_key = self.webhook
        self.gateway.flush_recordset()
        self.assertTrue(self.gateway.can_set_webhook)
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_02, self.webhook)
        result = (
            Store()
            .add_global_values(self.user._store_init_global_fields)
            ._build_result()
        )
        self.assertEqual(result["Store"]["gateways"], [self.gateway.id])
        self.assertTrue(result["Store"]["has_gateway_access"])
        # The partner has no gateway channels yet
        self.assertEqual(self._get_partner_store_info()["gateway_channel_ids"], [])
        # Assign the partner to the channel
        self.env["mail.guest.manage"].create(
            {
                "partner_id": self.partner.id,
                "guest_id": self._get_guest().id,
            }
        ).merge_partner()
        self.assertTrue(self.partner.gateway_channel_ids)
        self.assertEqual(
            self._get_partner_store_info()["gateway_channel_ids"],
            self.partner.gateway_channel_ids.ids,
        )

    def _get_guest(self):
        return self.env["mail.guest"].search(
            [
                ("gateway_token", "=", self.gateway_token),
                ("gateway_id", "=", self.gateway.id),
            ]
        )

    def test_incoming_message_author_is_guest(self):
        self.gateway.webhook_key = self.webhook
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
            self.set_message(self.message_01, self.webhook)
        channel = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        message = channel.message_ids
        self.assertEqual(len(message), 1)
        guest = self._get_guest()
        self.assertTrue(guest)
        self.assertEqual(message.author_guest_id, guest)
        self.assertFalse(message.author_id)
        self.assertEqual(message.gateway_type, "telegram")
        # Incoming messages are not sent back to Telegram
        self.assertFalse(message.notification_ids)

    def test_incoming_message_author_is_partner(self):
        self.gateway.webhook_key = self.webhook
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
            self.set_message(self.message_02, self.webhook)
        self.env["mail.guest.manage"].create(
            {"partner_id": self.partner.id, "guest_id": self._get_guest().id}
        ).merge_partner()
        with patch.object(telegram, "Bot", getMyBot()):
            self.set_message(self.message_01, self.webhook)
        channel = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertEqual(channel.message_ids.author_id, self.partner)
        self.assertFalse(channel.message_ids.author_guest_id)

    def test_post_message_sent_status(self):
        self.gateway.webhook_key = self.webhook
        with patch.object(telegram, "Bot", getMyBot(message_id=4321)):
            self.gateway.set_webhook()
            self.set_message(self.message_02, self.webhook)
            channel = self.env["discuss.channel"].search(
                [("gateway_id", "=", self.gateway.id)]
            )
            channel.message_post(
                body="HELLO",
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )
        notification = self.env["mail.notification"].search(
            [("gateway_channel_id", "=", channel.id)]
        )
        self.assertEqual(notification.notification_status, "sent")
        self.assertEqual(notification.gateway_message_id, "4321")
        self.assertFalse(notification.failure_reason)

    def test_send_to_partner_without_channel(self):
        """Sending to a partner gateway channel creates the discuss channel."""
        partner_channel = self.env["res.partner.gateway.channel"].create(
            {
                "partner_id": self.partner.id,
                "gateway_id": self.gateway.id,
                "gateway_token": self.gateway_token,
            }
        )
        self.assertFalse(
            self.env["discuss.channel"].search([("gateway_id", "=", self.gateway.id)])
        )
        with patch.object(telegram, "Bot", getMyBot()):
            message = self.partner.message_post(
                body="HELLO",
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
                gateway_notifications=[
                    {
                        "channel_type": "gateway",
                        "gateway_channel_id": partner_channel.id,
                        "partner_id": self.partner.id,
                    }
                ],
            )
        channel = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertTrue(channel)
        self.assertEqual(channel.gateway_channel_token, self.gateway_token)
        self.assertEqual(channel.name, self.partner.name)
        self.assertTrue(message.gateway_message_ids)

    def _post_incoming(self, message_vals):
        """Send an incoming update with the given message values and return
        the message posted on the channel."""
        message = dict(self.message_01["message"], **message_vals)
        if "location" in message_vals or "contact" in message_vals:
            message.pop("text")
        self.gateway.webhook_key = self.webhook
        with patch.object(telegram, "Bot", getMyBot()):
            self.gateway.set_webhook()
            self.set_message({"update_id": 1, "message": message}, self.webhook)
        return (
            self.env["discuss.channel"]
            .search([("gateway_id", "=", self.gateway.id)])
            .message_ids
        )

    def test_incoming_location(self):
        message = self._post_incoming(
            {"location": {"latitude": 40.357441, "longitude": 0.406973}}
        )
        self.assertIn(
            '<a target="_blank" rel="noopener noreferrer" '
            'href="https://www.google.com/maps/search/?api=1&amp;query='
            '40.357441,0.406973">Location</a>',
            message.body,
        )
        self.assertNotIn("&lt;a", message.body)

    def test_incoming_formatted_text(self):
        message = self._post_incoming(
            {
                "text": "Hi bold <friend>",
                "entities": [{"type": "bold", "offset": 3, "length": 4}],
            }
        )
        self.assertIn("<b>bold</b>", message.body)
        # User text is still escaped
        self.assertIn("&lt;friend&gt;", message.body)

    def test_incoming_contact_without_vcard(self):
        message = self._post_incoming(
            {
                "contact": {
                    "phone_number": "+34600000000",
                    "first_name": "Ana",
                    "last_name": "García; Pérez",
                }
            }
        )
        attachment = message.attachment_ids
        self.assertEqual(attachment.name, "Ana.vcf")
        vcard = attachment.raw.decode()
        self.assertIn(r"N:García\; Pérez;Ana;;;", vcard)
        self.assertIn("TEL;TYPE=CELL:+34600000000", vcard)

    def test_incoming_contact_with_vcard(self):
        vcard = "BEGIN:VCARD\r\nVERSION:3.0\r\nFN:Ana\r\nEND:VCARD\r\n"
        message = self._post_incoming(
            {
                "contact": {
                    "phone_number": "+34600000000",
                    "first_name": "Ana",
                    "vcard": vcard,
                }
            }
        )
        self.assertEqual(message.attachment_ids.raw.decode(), vcard)
