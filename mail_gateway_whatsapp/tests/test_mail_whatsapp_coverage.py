# Copyright 2025 Komit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from unittest.mock import patch

import requests

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged

from odoo.addons.mail_gateway.tests.common import MailGatewayTestCase


@tagged("-at_install", "post_install")
class TestMailWhatsAppCoverage(MailGatewayTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gateway = cls.env["mail.gateway"].create(
            {
                "name": "gateway",
                "gateway_type": "whatsapp",
                "token": "token",
                "whatsapp_security_key": "key",
                "whatsapp_account_id": "123456",
                "whatsapp_from_phone": "111",
                "webhook_secret": "MY-SECRET",
                "member_ids": [(4, cls.env.user.id)],
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "Ada Lovelace", "phone": "+34900111222"}
        )

    def _create_template(self, **kwargs):
        vals = {
            "name": "Template",
            "category": "utility",
            "language": "es",
            "body": "Body",
            "gateway_id": self.gateway.id,
            "state": "approved",
            "is_supported": True,
        }
        vals.update(kwargs)
        return self.env["mail.whatsapp.template"].create(vals)

    # ------------------------------------------------------------------
    # Template constraints
    # ------------------------------------------------------------------
    def test_check_buttons_max_total(self):
        tmpl = self._create_template()
        with self.assertRaisesRegex(ValidationError, "maximum of 10 buttons"):
            tmpl.write(
                {
                    "button_ids": [
                        Command.create({"name": f"B{i}", "button_type": "quick_reply"})
                        for i in range(11)
                    ]
                }
            )

    def test_check_buttons_max_url(self):
        tmpl = self._create_template()
        with self.assertRaisesRegex(ValidationError, "maximum of 2 URL buttons"):
            tmpl.write(
                {
                    "button_ids": [
                        Command.create(
                            {
                                "name": f"U{i}",
                                "button_type": "url",
                                "website_url": "https://example.com",
                            }
                        )
                        for i in range(3)
                    ]
                }
            )

    def test_check_buttons_max_phone(self):
        tmpl = self._create_template()
        with self.assertRaisesRegex(ValidationError, "maximum of 1 Call Number"):
            tmpl.write(
                {
                    "button_ids": [
                        Command.create(
                            {
                                "name": f"P{i}",
                                "button_type": "phone_number",
                                "call_number": "+34600000000",
                            }
                        )
                        for i in range(2)
                    ]
                }
            )

    def test_check_variables_two_headers(self):
        with self.assertRaisesRegex(
            ValidationError, "exactly 1 variable in the header"
        ):
            self._create_template(
                header="{{1}} {{2}}",
                variable_ids=[
                    Command.create(
                        {"name": "{{1}}", "line_type": "header", "field_name": "name"}
                    ),
                    Command.create(
                        {"name": "{{2}}", "line_type": "header", "field_name": "phone"}
                    ),
                ],
            )

    def test_check_variables_header_index(self):
        with self.assertRaisesRegex(ValidationError, r"header should be used as"):
            self._create_template(
                header="{{2}}",
                variable_ids=[
                    Command.create(
                        {"name": "{{2}}", "line_type": "header", "field_name": "name"}
                    ),
                ],
            )

    def test_check_variables_body_gap(self):
        with self.assertRaisesRegex(ValidationError, "should start at 1"):
            self._create_template(
                body="{{1}} {{3}}",
                variable_ids=[
                    Command.create(
                        {"name": "{{1}}", "line_type": "body", "field_name": "name"}
                    ),
                    Command.create(
                        {"name": "{{3}}", "line_type": "body", "field_name": "phone"}
                    ),
                ],
            )

    def test_variable_check_name_invalid(self):
        tmpl = self._create_template()
        with self.assertRaisesRegex(ValidationError, "format"):
            self.env["mail.whatsapp.template.variable"].create(
                {
                    "name": "not-a-var",
                    "line_type": "body",
                    "template_id": tmpl.id,
                    "field_name": "name",
                }
            )

    def test_variable_check_field_name_missing(self):
        tmpl = self._create_template()
        with self.assertRaisesRegex(ValidationError, "associated with a field"):
            self.env["mail.whatsapp.template.variable"].create(
                {
                    "name": "{{1}}",
                    "line_type": "body",
                    "template_id": tmpl.id,
                    "field_name": False,
                }
            )

    def test_variable_check_field_name_invalid_path(self):
        tmpl = self._create_template()
        with self.assertRaisesRegex(ValidationError, "valid field path"):
            self.env["mail.whatsapp.template.variable"].create(
                {
                    "name": "{{1}}",
                    "line_type": "body",
                    "template_id": tmpl.id,
                    "field_name": "not_a_real_field",
                }
            )

    # ------------------------------------------------------------------
    # Button constraints
    # ------------------------------------------------------------------
    def test_button_invalid_url(self):
        tmpl = self._create_template()
        with self.assertRaisesRegex(ValidationError, "valid URL"):
            self.env["mail.whatsapp.template.button"].create(
                {
                    "name": "Web",
                    "button_type": "url",
                    "website_url": "not-a-url",
                    "template_id": tmpl.id,
                }
            )

    def test_button_check_variable_ids(self):
        tmpl = self._create_template()
        static_button = self.env["mail.whatsapp.template.button"].create(
            {
                "name": "Static",
                "button_type": "url",
                "url_type": "static",
                "website_url": "https://example.com",
                "template_id": tmpl.id,
            }
        )
        # A dynamic url auto-creates its placeholder variable
        dynamic_button = self.env["mail.whatsapp.template.button"].create(
            {
                "name": "{{1}}",
                "button_type": "url",
                "url_type": "dynamic",
                "website_url": "https://example.com/",
                "template_id": tmpl.id,
            }
        )
        self.assertTrue(dynamic_button.variable_ids)
        dynamic_button.check_variable_ids()
        # A static url with a placeholder variable is invalid
        static_button.variable_ids = [
            Command.create(
                {
                    "name": "{{1}}",
                    "line_type": "button",
                    "template_id": tmpl.id,
                    "field_name": "name",
                }
            )
        ]
        with self.assertRaises(ValidationError):
            static_button.check_variable_ids()

    # ------------------------------------------------------------------
    # Export / import component building
    # ------------------------------------------------------------------
    def test_prepare_components_to_export(self):
        tmpl = self._create_template(
            header="Hello {{1}}",
            footer="Bye",
            body="Body {{1}}",
            variable_ids=[
                Command.create(
                    {"name": "{{1}}", "line_type": "header", "field_name": "name"}
                ),
                Command.create(
                    {"name": "{{1}}", "line_type": "body", "field_name": "name"}
                ),
            ],
        )
        self.env["mail.whatsapp.template.button"].create(
            {
                "name": "{{1}}",
                "button_type": "url",
                "url_type": "dynamic",
                "website_url": "https://example.com/",
                "template_id": tmpl.id,
            }
        )
        self.env["mail.whatsapp.template.button"].create(
            {
                "name": "Call",
                "button_type": "phone_number",
                "call_number": "+34600000000",
                "template_id": tmpl.id,
            }
        )
        components = tmpl._prepare_components_to_export()
        types = {c["type"] for c in components}
        self.assertEqual(types, {"BODY", "HEADER", "FOOTER", "BUTTONS"})
        buttons = next(c for c in components if c["type"] == "BUTTONS")["buttons"]
        button_types = {b["type"] for b in buttons}
        self.assertEqual(button_types, {"URL", "PHONE_NUMBER"})

    def test_prepare_values_to_import_button_update_and_unsupported(self):
        tmpl = self._create_template(template_uid="999")
        existing = self.env["mail.whatsapp.template.button"].create(
            {
                "name": "Existing",
                "button_type": "quick_reply",
                "template_id": tmpl.id,
            }
        )
        json_data = {
            "name": "imported_tmpl",
            "category": "MARKETING",
            "language": "es",
            "status": "APPROVED",
            "id": "999",
            "components": [
                {"type": "BODY", "text": "Body"},
                {
                    "type": "BUTTONS",
                    "buttons": [{"type": "QUICK_REPLY", "text": "Existing"}],
                },
                {"type": "CAROUSEL"},  # unsupported -> is_supported False
            ],
        }
        vals = tmpl._prepare_values_to_import(self.gateway, json_data)
        self.assertFalse(vals["is_supported"])
        # button update command referencing the existing button
        button_cmds = vals["button_ids"]
        self.assertTrue(
            any(
                cmd[0] == Command.UPDATE and cmd[1] == existing.id
                for cmd in button_cmds
            )
        )

    def test_button_export_template_http_error(self):
        tmpl = self._create_template()

        def _bad_response(*args, **kwargs):
            response = requests.Response()
            response.status_code = 400
            response._content = b'{"error": "bad"}'
            response.url = args[0] if args else ""
            return response

        with patch.object(requests, "post", _bad_response):
            with self.assertRaises(UserError):
                tmpl.button_export_template()

        # a non-HTTP error is also wrapped into a UserError
        def _raise(*args, **kwargs):
            raise ValueError("boom")

        with patch.object(requests, "post", _raise):
            with self.assertRaises(UserError):
                tmpl.button_export_template()

    def test_sync_template_error(self):
        tmpl = self._create_template(template_uid="123")

        def _raise(*args, **kwargs):
            raise ValueError("boom")

        with patch.object(requests, "get", _raise):
            with self.assertRaises(UserError):
                tmpl.button_sync_template()

    def test_import_template_request_error(self):
        self.gateway.whatsapp_account_id = "123456"

        def _raise(*args, **kwargs):
            raise ValueError("network down")

        with patch.object(requests, "get", _raise):
            with self.assertRaises(UserError):
                self.gateway.button_import_whatsapp_template()

    def test_button_dynamic_placeholder_name(self):
        tmpl = self._create_template()
        button = self.env["mail.whatsapp.template.button"].create(
            {
                "name": "{{2}}",
                "button_type": "url",
                "url_type": "dynamic",
                "website_url": "https://example.com/",
                "template_id": tmpl.id,
            }
        )
        # the auto-generated placeholder is not named {{1}}
        with self.assertRaisesRegex(ValidationError, r"can only be"):
            button.check_variable_ids()

    # ------------------------------------------------------------------
    # Rendering / value extraction
    # ------------------------------------------------------------------
    def test_render_body_message_default_res_ids(self):
        tmpl = self._create_template(
            header="Hi {{1}}",
            body="Name {{1}}",
            variable_ids=[
                Command.create(
                    {"name": "{{1}}", "line_type": "header", "field_name": "name"}
                ),
                Command.create(
                    {"name": "{{1}}", "line_type": "body", "field_name": "name"}
                ),
            ],
        )
        rendered = tmpl.with_context(
            default_res_ids=[self.partner.id]
        ).render_body_message()
        self.assertIn(self.partner.name, rendered)

    def test_extract_value_from_field_path_variants(self):
        parent = self.env["res.partner"].create({"name": "Parent Co"})
        self.partner.parent_id = parent
        tmpl = self._create_template(
            body="{{1}}",
            variable_ids=[
                Command.create(
                    {"name": "{{1}}", "line_type": "body", "field_name": "parent_id"}
                ),
            ],
        )
        var = tmpl.variable_ids
        # relational field -> display name of the related record
        self.assertEqual(
            var._get_variables_value(self.partner), {"body-{{1}}": "Parent Co"}
        )
        # chained path -> last model + last field name
        var.field_name = "parent_id.name"
        self.assertEqual(var._extract_value_from_field_path(self.partner), "Parent Co")
        # selection field -> exported label
        var.field_name = "type"
        self.assertTrue(var._extract_value_from_field_path(self.partner))

    def test_variable_display_name_and_onchange(self):
        tmpl = self._create_template()
        Variable = self.env["mail.whatsapp.template.variable"]
        # display name: header variant vs body variant
        header_var = Variable.new(
            {"name": "{{1}}", "line_type": "header", "template_id": tmpl.id}
        )
        body_var = Variable.new(
            {"name": "{{1}}", "line_type": "body", "template_id": tmpl.id}
        )
        self.assertTrue(header_var.display_name)
        self.assertIn("{{1}}", body_var.display_name)
        # onchange resets the field on an in-memory record (no constraint flush)
        onchange_var = Variable.new(
            {
                "name": "{{1}}",
                "line_type": "body",
                "template_id": tmpl.id,
                "field_name": "name",
            }
        )
        onchange_var._onchange_model_id()
        self.assertFalse(onchange_var.field_name)

    def test_button_back2draft(self):
        tmpl = self._create_template()
        tmpl.button_back2draft()
        self.assertEqual(tmpl.state, "draft")

    # ------------------------------------------------------------------
    # discuss.channel avatar
    # ------------------------------------------------------------------
    def test_generate_avatar_gateway_whatsapp(self):
        channel = self.partner._whatsapp_get_channel("phone", self.gateway)
        avatar = channel._generate_avatar_gateway()
        self.assertIn("<svg", avatar)

    def test_generate_avatar_gateway_non_whatsapp(self):
        # A non-whatsapp gateway channel falls back to super() (returns False)
        other_gateway = self.env["mail.gateway"].create(
            {
                "name": "abstract gateway",
                "gateway_type": "abstract",
                "token": "abs-token",
                "webhook_secret": "ABS-SECRET",
            }
        )
        channel = self.env["discuss.channel"].create(
            {
                "name": "abstract channel",
                "gateway_id": other_gateway.id,
                "channel_type": "gateway",
            }
        )
        self.assertFalse(channel._generate_avatar_gateway())

    # ------------------------------------------------------------------
    # Inbound status updates
    # ------------------------------------------------------------------
    def test_receive_update_status_failed(self):
        service = self.env["mail.gateway.whatsapp"]
        channel = self.partner._whatsapp_get_channel("phone", self.gateway)
        token = channel.gateway_channel_token
        message = channel.with_context(no_gateway_notification=True).message_post(
            body="hi", message_type="comment", subtype_xmlid="mail.mt_comment"
        )
        notification = self.env["mail.notification"].create(
            {
                "mail_message_id": message.id,
                "notification_type": "gateway",
                "gateway_channel_id": channel.id,
                "gateway_message_id": "wamid.TEST",
                "res_partner_id": self.partner.id,
            }
        )
        update = {
            "entry": [
                {
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "statuses": [
                                    # non-failed status is ignored
                                    {
                                        "recipient_id": token,
                                        "id": "wamid.TEST",
                                        "status": "delivered",
                                    },
                                    # unknown recipient -> no channel, skipped
                                    {
                                        "recipient_id": "0000",
                                        "id": "wamid.TEST",
                                        "status": "failed",
                                    },
                                    # failed status without a matching notification
                                    {
                                        "recipient_id": token,
                                        "id": "wamid.UNKNOWN",
                                        "status": "failed",
                                    },
                                    # failed status updating our notification
                                    {
                                        "recipient_id": token,
                                        "id": "wamid.TEST",
                                        "status": "failed",
                                        "errors": [
                                            {
                                                "code": 131,
                                                "error_data": {"details": "Boom"},
                                            }
                                        ],
                                    },
                                ]
                            },
                        }
                    ]
                }
            ]
        }
        service._receive_update(self.gateway, update)
        self.assertEqual(notification.notification_status, "exception")
        self.assertIn("Boom", notification.failure_reason)

    def test_receive_update_image_and_location(self):
        service = self.env["mail.gateway.whatsapp"]
        token = self.partner.phone.replace("+", "").replace(" ", "")

        def fake_get(url, *args, **kwargs):
            response = requests.Response()
            response.status_code = 200
            if "cdn" in url:
                response._content = b"IMAGEBYTES"
            else:
                response._content = json.dumps(
                    {"url": "https://cdn.example.com/img", "mime_type": "image/png"}
                ).encode()
            return response

        value = {
            "messaging_product": "whatsapp",
            "contacts": [{"wa_id": token, "profile": {"name": "Ada"}}],
            "messages": [
                {
                    "from": token,
                    "id": "wamid.IMG",
                    "timestamp": "1700000000",
                    "type": "image",
                    "image": {"id": "IMG_ID", "caption": "Nice pic"},
                },
                {
                    "from": token,
                    "id": "wamid.LOC",
                    "timestamp": "1700000001",
                    "type": "location",
                    "location": {"latitude": "1.23", "longitude": "4.56"},
                },
            ],
        }
        update = {"entry": [{"changes": [{"field": "messages", "value": value}]}]}
        # The controller processes inbound updates with ``no_gateway_notification``
        # so incoming messages are not echoed back to the Meta API.
        gateway = self.gateway.with_context(no_gateway_notification=True)
        with patch.object(requests, "get", fake_get):
            service._receive_update(gateway, update)
        channel = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertTrue(channel.message_ids)
        self.assertTrue(channel.message_ids.attachment_ids)

    # ------------------------------------------------------------------
    # mail.thread helpers
    # ------------------------------------------------------------------
    def test_get_whatsapp_channel_vals(self):
        Partner = self.env["res.partner"]
        vals = Partner._get_whatsapp_channel_vals("3412345", self.gateway, self.partner)
        self.assertEqual(vals["gateway_channel_token"], "3412345")
        self.assertEqual(vals["partner_id"], self.partner.id)
        vals_no_partner = Partner._get_whatsapp_channel_vals(
            "3412345", self.gateway, Partner.browse()
        )
        self.assertNotIn("partner_id", vals_no_partner)

    def test_whatsapp_get_channel_creates_gateway_channel(self):
        channel = self.partner._whatsapp_get_channel("phone", self.gateway)
        self.assertTrue(channel)
        gateway_channel = self.env["res.partner.gateway.channel"].search(
            [
                ("partner_id", "=", self.partner.id),
                ("gateway_id", "=", self.gateway.id),
            ]
        )
        self.assertTrue(gateway_channel)
        # a second call reuses the existing gateway channel
        self.partner._whatsapp_get_channel("phone", self.gateway)
        self.assertEqual(
            self.env["res.partner.gateway.channel"].search_count(
                [
                    ("partner_id", "=", self.partner.id),
                    ("gateway_id", "=", self.gateway.id),
                ]
            ),
            1,
        )

    def test_whatsapp_get_channel_no_phone(self):
        partner = self.env["res.partner"].create({"name": "No Phone"})
        with self.assertRaisesRegex(UserError, "Phone cannot be sanitized"):
            partner._whatsapp_get_channel("phone", self.gateway)

    # ------------------------------------------------------------------
    # ir.actions.server
    # ------------------------------------------------------------------
    def test_server_action_model_coherency(self):
        with self.assertRaisesRegex(ValidationError, "non transient mail.thread"):
            self.env["ir.actions.server"].create(
                {
                    "name": "WA transient",
                    "model_id": self.env["ir.model"]._get_id("res.users.settings"),
                    "state": "whatsapp",
                    "whatsapp_gateway_id": self.gateway.id,
                }
            )

    def test_server_action_run_whatsapp(self):
        tmpl = self._create_template(
            model_id=self.env["ir.model"]._get_id("res.partner"),
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "WA action",
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "state": "whatsapp",
                "whatsapp_gateway_id": self.gateway.id,
                "whatsapp_partner": "{{ object.id }}",
                "whatsapp_template_id": tmpl.id,
            }
        )
        self.assertTrue(action.available_model_ids)
        service_cls = type(self.env["mail.gateway.whatsapp"])
        with patch.object(service_cls, "_send", return_value=None):
            action.with_context(
                active_model="res.partner",
                active_ids=self.partner.ids,
                active_id=self.partner.id,
            ).run()
        channel = self.env["discuss.channel"].search(
            [("gateway_id", "=", self.gateway.id)]
        )
        self.assertTrue(channel)

    def test_server_action_run_whatsapp_no_active_ids(self):
        tmpl = self._create_template(
            model_id=self.env["ir.model"]._get_id("res.partner"),
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "WA action noctx",
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "state": "whatsapp",
                "whatsapp_gateway_id": self.gateway.id,
                "whatsapp_partner": "{{ object.id }}",
                "whatsapp_template_id": tmpl.id,
            }
        )
        # No active_ids/active_id -> action does nothing
        self.assertFalse(action._run_action_whatsapp_multi())

    # ------------------------------------------------------------------
    # Wizards
    # ------------------------------------------------------------------
    def test_whatsapp_composer(self):
        composer = (
            self.env["whatsapp.composer"]
            .with_context(
                active_model="res.partner",
                active_id=self.partner.id,
            )
            .create(
                {
                    "res_model": "res.partner",
                    "res_id": self.partner.id,
                    "number_field_name": "phone",
                    "gateway_id": self.gateway.id,
                }
            )
        )
        # is_required_template computed with no previous message -> True
        self.assertTrue(composer.is_required_template)
        composer.onchange_gateway_id()
        self.assertFalse(composer.template_id)
        # Sending without body raises
        with self.assertRaisesRegex(UserError, "Body is required"):
            composer.action_send_whatsapp()
        # With body -> posts a message on the channel
        composer.body = "Hello"
        service_cls = type(self.env["mail.gateway.whatsapp"])
        with patch.object(service_cls, "_send", return_value=None):
            composer.action_send_whatsapp()
        action = composer.action_view_whatsapp()
        self.assertEqual(action["tag"], "mail.action_discuss")

    def test_whatsapp_composer_not_required_template(self):
        # Missing number_field_name -> template is not required
        composer = self.env["whatsapp.composer"].create(
            {
                "res_model": "res.partner",
                "res_id": self.partner.id,
                "gateway_id": self.gateway.id,
            }
        )
        self.assertFalse(composer.is_required_template)

    def test_whatsapp_composer_default_get_multiple(self):
        # A second whatsapp gateway -> the wizard cannot auto-pick one
        self.env["mail.gateway"].create(
            {
                "name": "gateway 2",
                "gateway_type": "whatsapp",
                "token": "token2",
                "whatsapp_security_key": "key2",
                "webhook_secret": "SECRET-2",
            }
        )
        defaults = self.env["whatsapp.composer"].default_get(
            ["find_gateway", "gateway_id"]
        )
        self.assertTrue(defaults["find_gateway"])

    def test_prepare_value_to_send_res_id_context(self):
        tmpl = self._create_template(
            body="Hi {{1}}",
            model_id=self.env["ir.model"]._get_id("res.partner"),
            variable_ids=[
                Command.create(
                    {"name": "{{1}}", "line_type": "body", "field_name": "name"}
                ),
            ],
        )
        # prepare_value_to_send resolves the record from the ``res_id`` context
        components = tmpl.with_context(res_id=self.partner.id).prepare_value_to_send()
        body = next(c for c in components if c["type"] == "body")
        self.assertEqual(body["parameters"][0]["text"], self.partner.name)

    def test_whatsapp_composer_default_get(self):
        defaults = self.env["whatsapp.composer"].default_get(
            ["find_gateway", "gateway_id"]
        )
        # Only one whatsapp gateway exists -> auto-selected
        self.assertFalse(defaults["find_gateway"])
        self.assertEqual(defaults["gateway_id"], self.gateway.id)

    def test_compose_gateway_message_template(self):
        tmpl = self._create_template(
            body="Hello world",
            model_id=self.env["ir.model"]._get_id("res.partner"),
        )
        composer = self.env["mail.compose.gateway.message"].create(
            {
                "model": "res.partner",
                "res_ids": f"[{self.partner.id}]",
                "whatsapp_template_id": tmpl.id,
            }
        )
        composer.onchange_whatsapp_template_id()
        self.assertTrue(composer.body)
        # sending applies the whatsapp template context branch
        service_cls = type(self.env["mail.gateway.whatsapp"])
        with patch.object(service_cls, "_send", return_value=None):
            composer._action_send_mail()
