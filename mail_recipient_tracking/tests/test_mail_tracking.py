# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64
import time
from unittest.mock import Mock, patch

from lxml import etree
from werkzeug.exceptions import BadRequest

from odoo import SUPERUSER_ID, fields, http
from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import HttpCaseWithUserDemo, MockSmtplibCase
from odoo.addons.mail.models.mail_thread import MailThread as CoreMailThread
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail_tracking.controllers.main import (
    BLANK,
    MailTrackingController,
    db_env,
)

mock_send_email = "odoo.addons.base.models.ir_mail_server.IrMail_Server.send_email"


class FakeUserAgent:
    browser = "Test browser"
    platform = "Test platform"

    def __str__(self):
        """Return name"""
        return "Test suite"


class TestMailTracking(TransactionCase, MockSmtplibCase):
    patch_http_request = True

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        # Keep a dedicated company alias domain. Otherwise, temporary alias domains
        # created by tests may become referenced by aliases created by other modules.
        self.alias_domain_dummy = self.env["mail.alias.domain"].create(
            {"name": "mailtracking-dummy-domain.test"}
        )
        self.env.company.alias_domain_id = self.alias_domain_dummy
        self.sender = self.env["res.partner"].create(
            {"name": "Test sender", "email": "sender@example.com"}
        )
        self.recipient = self.env["res.partner"].create(
            {"name": "Test recipient", "email": "recipient@example.com"}
        )
        self.last_request = None
        if self.patch_http_request:
            self.last_request = http.request
            http.request = type(
                "obj",
                (object,),
                {
                    "env": self.env,
                    "cr": self.env.cr,
                    "db": self.env.cr.dbname,
                    "endpoint": type("obj", (object,), {"routing": []}),
                    "httprequest": type(
                        "obj",
                        (object,),
                        {
                            "remote_addr": "123.123.123.123",
                            "user_agent": FakeUserAgent(),
                        },
                    ),
                },
            )
            for _ in http._generate_routing_rules(
                ["mail", "mail_tracking"], nodb_only=False
            ):
                pass

    def tearDown(self, *args, **kwargs):
        if self.patch_http_request:
            http.request = self.last_request
        return super().tearDown(*args, **kwargs)

    def test_empty_email(self):
        self.recipient.write({"email_bounced": True})
        self.recipient.write({"email": False})
        self.assertEqual(False, self.recipient.email)
        self.assertEqual(False, self.recipient.email_bounced)
        self.recipient.write({"email_bounced": True})
        self.recipient.write({"email": ""})
        self.assertEqual(False, self.recipient.email_bounced)
        self.assertEqual(False, self.env["mail.tracking.email"].email_is_bounced(False))
        self.assertEqual(
            0.0, self.env["mail.tracking.email"].email_score_from_email(False)
        )

    def test_recipient_address_compute(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.write({"recipient": False})
        self.assertEqual(False, tracking.recipient_address)

    def test_message_post(self):
        # This message will generate a notification for recipient
        message = self.env["mail.message"].create(
            {
                "subject": "Message test",
                "author_id": self.sender.id,
                "email_from": self.sender.email,
                "message_type": "comment",
                "model": "res.partner",
                "res_id": self.recipient.id,
                "partner_ids": [Command.link(self.recipient.id)],
                "body": "<p>This is a test message</p>",
            }
        )
        if message._is_thread_message():
            with self.mock_smtplib_connection():
                self.env[message.model].browse(message.res_id).with_context(
                    mail_notify_force_send=True
                )._notify_thread(message)
        # Search tracking created
        tracking_email = self.env["mail.tracking.email"].search(
            [
                ("mail_message_id", "=", message.id),
                ("partner_id", "=", self.recipient.id),
            ]
        )
        # The tracking email must be sent
        self.assertTrue(tracking_email)
        self.assertEqual(tracking_email.state, "sent")
        # message_dict read by web interface
        message_dict = Store().add(message).get_result()
        # First partner is recipient
        partner_id = message_dict["mail.message"][0]["partner_trackings"][0][
            "partner_id"
        ]
        self.assertEqual(partner_id, self.recipient.id)
        status = message_dict["mail.message"][0]["partner_trackings"][0]
        # Tracking status must be sent and
        # mail tracking must be the one search before
        self.assertEqual(status["status"], "sent")
        self.assertEqual(status["tracking_id"], tracking_email.id)
        self.assertEqual(status["recipient"], self.recipient.display_name)
        self.assertEqual(status["partner_id"], self.recipient.id)
        self.assertEqual(status["isCc"], False)
        # And now open the email
        metadata = {
            "ip": "127.0.0.1",
            "user_agent": "Odoo Test/1.0",
            "os_family": "linux",
            "ua_family": "odoo",
        }
        tracking_email.event_create("open", metadata)
        self.assertEqual(tracking_email.state, "opened")

    def test_message_post_partner_no_email(self):
        # Create message with recipient without defined email
        self.recipient.write({"email": False})
        message = self.env["mail.message"].create(
            {
                "subject": "Message test",
                "author_id": self.sender.id,
                "email_from": self.sender.email,
                "message_type": "comment",
                "model": "res.partner",
                "res_id": self.recipient.id,
                "partner_ids": [Command.link(self.recipient.id)],
                "body": "<p>This is a test message</p>",
            }
        )
        if message._is_thread_message():
            with self.mock_smtplib_connection():
                self.env[message.model].browse(message.res_id).with_context(
                    do_not_send_copy=True, mail_notify_force_send=True
                )._notify_thread(message)
        # Search tracking created
        tracking_email = self.env["mail.tracking.email"].search(
            [
                ("mail_message_id", "=", message.id),
                ("partner_id", "=", self.recipient.id),
            ]
        )
        # No email should generate a error state: no_recipient
        self.assertEqual(tracking_email.state, "error")
        self.assertEqual(tracking_email.error_type, "no_recipient")
        self.assertFalse(self.recipient.email_bounced)

    def test_message_post_show_aliases(self):
        # Create message with show aliases setup
        self.env.company.mail_tracking_show_aliases = True
        # Setup catchall domain
        IrConfigParamObj = self.env["ir.config_parameter"].sudo()
        IrConfigParamObj.set_param("mail.catchall.domain", "test.com")
        # pylint: disable=C8107
        message = self.env["mail.message"].create(
            {
                "subject": "Message test",
                "author_id": self.sender.id,
                "email_from": self.sender.email,
                "message_type": "comment",
                "model": "res.partner",
                "res_id": self.recipient.id,
                "partner_ids": [(4, self.recipient.id)],
                "email_cc": "Dominique Pinon <unnamed@test.com>, customer-invoices@test.com",  # noqa E501
                "body": "<p>This is another test message</p>",
            }
        )
        message_dict = Store().add(message).get_result()
        partner_trackings = message_dict["mail.message"][0]["partner_trackings"]
        self.assertTrue(
            any(
                [
                    tracking["recipient"] == "customer-invoices@test.com"
                    for tracking in partner_trackings
                ]
            )
        )

    def test_tracking_email_get(self):
        mail_server = self.env["ir.mail_server"]
        _mail, tracking = self.mail_send(self.recipient.email)
        _other_mail, other_tracking = self.mail_send(self.recipient.email)

        tracking_email = mail_server._tracking_email_get(
            {"X-Odoo-MailTracking-ID": str(tracking.id)}
        )
        self.assertEqual(tracking_email, tracking)

        deprecated_tracking_email = mail_server._tracking_email_get(
            {"X-Odoo-Tracking-ID": str(tracking.id)}
        )
        self.assertEqual(deprecated_tracking_email, tracking)

        preferred_tracking_email = mail_server._tracking_email_get(
            {
                "X-Odoo-MailTracking-ID": str(tracking.id),
                "X-Odoo-Tracking-ID": str(other_tracking.id),
            }
        )
        self.assertEqual(preferred_tracking_email, tracking)

        missing_tracking_email = mail_server._tracking_email_get({})
        self.assertFalse(missing_tracking_email)

        invalid_tracking_email = mail_server._tracking_email_get(
            {"X-Odoo-MailTracking-ID": "invalid"}
        )
        self.assertFalse(invalid_tracking_email)

    def test_mail_alias_cache_invalidation(self):
        alias_model = self.env["mail.alias"]
        alias_domain = self.env["mail.alias.domain"].create(
            {"name": "mailtracking-cache.test"}
        )
        model = self.env["ir.model"]._get("res.partner")

        aliases_before_create = alias_model.get_aliases()
        self.assertNotIn(
            "mailtracking-create@mailtracking-cache.test", aliases_before_create
        )

        alias = alias_model.create(
            {
                "alias_name": "mailtracking-create",
                "alias_domain_id": alias_domain.id,
                "alias_model_id": model.id,
            }
        )

        aliases_after_create = alias_model.get_aliases()
        self.assertIn(alias.display_name, aliases_after_create)

        alias.write({"alias_name": "mailtracking-write"})
        aliases_after_write = alias_model.get_aliases()
        self.assertIn("mailtracking-write@mailtracking-cache.test", aliases_after_write)
        self.assertNotIn(
            "mailtracking-create@mailtracking-cache.test", aliases_after_write
        )

        alias.unlink()
        aliases_after_unlink = alias_model.get_aliases()
        self.assertNotIn(
            "mailtracking-write@mailtracking-cache.test", aliases_after_unlink
        )

    def test_mail_alias_domain_cache_invalidation(self):
        alias_model = self.env["mail.alias"]

        aliases_before_create = alias_model.get_aliases()
        self.assertNotIn(
            "mailtracking-catchall@mailtracking-domain-cache.test",
            aliases_before_create,
        )
        self.assertNotIn(
            "mailtracking-default@mailtracking-domain-cache.test",
            aliases_before_create,
        )

        alias_domain = self.env["mail.alias.domain"].create(
            {
                "name": "mailtracking-domain-cache.test",
                "catchall_alias": "mailtracking-catchall",
                "default_from": "mailtracking-default",
            }
        )

        aliases_after_create = alias_model.get_aliases()
        self.assertIn(
            "mailtracking-catchall@mailtracking-domain-cache.test",
            aliases_after_create,
        )
        self.assertIn(
            "mailtracking-default@mailtracking-domain-cache.test",
            aliases_after_create,
        )

        alias_domain.write({"catchall_alias": "mailtracking-catchall-updated"})
        aliases_after_write = alias_model.get_aliases()
        self.assertIn(
            "mailtracking-catchall-updated@mailtracking-domain-cache.test",
            aliases_after_write,
        )
        self.assertNotIn(
            "mailtracking-catchall@mailtracking-domain-cache.test",
            aliases_after_write,
        )

        alias_domain.unlink()
        aliases_after_unlink = alias_model.get_aliases()
        self.assertNotIn(
            "mailtracking-catchall-updated@mailtracking-domain-cache.test",
            aliases_after_unlink,
        )
        self.assertNotIn(
            "mailtracking-default@mailtracking-domain-cache.test",
            aliases_after_unlink,
        )

    def test_get_view_adds_failed_messages_filter(self):
        partner_model = self.env["res.partner"]

        search_view = partner_model.get_view(view_type="search")
        search_doc = etree.XML(search_view["arch"])
        failed_filters = search_doc.xpath("//search/filter[@name='failed_message_ids']")

        self.assertEqual(len(failed_filters), 1)
        self.assertEqual(
            failed_filters[0].get("string"), self.env._("Failed sent messages")
        )
        self.assertEqual(
            failed_filters[0].get("domain"),
            str(
                [
                    [
                        "failed_message_ids.mail_tracking_ids.state",
                        "in",
                        list(self.env["mail.message"].get_failed_states()),
                    ],
                    [
                        "failed_message_ids.mail_tracking_needs_action",
                        "=",
                        True,
                    ],
                ]
            ),
        )
        self.assertEqual(
            failed_filters[0].getprevious().tag,
            "separator",
        )

        form_view = partner_model.get_view(view_type="form")
        form_doc = etree.XML(form_view["arch"])
        self.assertFalse(form_doc.xpath("//filter[@name='failed_message_ids']"))

    def test_message_route_process(self):
        partner_model = self.env["res.partner"]
        message = Mock()
        routes = [("res.partner", False, {}, self.env.user.id, False)]

        message_dict = {
            "cc": "copy@example.com",
            "to": "recipient@example.com",
            "message_id": "test-message-id",
            # Optional mail headers used by mail.thread overrides (e.g. mass_mailing).
            "references": "",
            "in_reply_to": "",
        }
        with patch.object(
            CoreMailThread,
            "_message_route_process",
            autospec=True,
            return_value="delegated",
        ) as mock_super:
            result = partner_model._message_route_process(message, message_dict, routes)

        self.assertEqual(result, "delegated")
        self.assertEqual(message_dict["email_cc"], "copy@example.com")
        self.assertEqual(message_dict["email_to"], "recipient@example.com")
        self.assertEqual(mock_super.call_args.args[2]["email_cc"], "copy@example.com")
        self.assertEqual(
            mock_super.call_args.args[2]["email_to"], "recipient@example.com"
        )

        message_dict = {
            "message_id": "test-message-id",
            # Optional mail headers used by mail.thread overrides (e.g. mass_mailing).
            "references": "",
            "in_reply_to": "",
        }
        with patch.object(
            CoreMailThread,
            "_message_route_process",
            autospec=True,
            return_value="delegated-empty",
        ) as mock_super:
            result = partner_model._message_route_process(message, message_dict, routes)

        self.assertEqual(result, "delegated-empty")
        self.assertFalse(message_dict["email_cc"])
        self.assertFalse(message_dict["email_to"])
        self.assertFalse(mock_super.call_args.args[2]["email_cc"])
        self.assertFalse(mock_super.call_args.args[2]["email_to"])

    def _check_partner_trackings_cc(self, message):
        message_dict = Store().add(message).get_result()
        partner_trackings = message_dict["mail.message"][0]["partner_trackings"]
        self.assertEqual(len(partner_trackings), 3)
        # mail cc
        foundPartner = False
        foundNoPartner = False
        for tracking in partner_trackings:
            if tracking["partner_id"] == self.sender.id:
                foundPartner = True
                self.assertTrue(tracking["isCc"])
            elif tracking["recipient"] == "unnamed@test.com":
                foundNoPartner = True
                self.assertFalse(tracking["partner_id"])
                self.assertTrue(tracking["isCc"])
            elif tracking["partner_id"] == self.recipient.id:
                self.assertFalse(tracking["isCc"])
        self.assertTrue(foundPartner)
        self.assertTrue(foundNoPartner)

    def test_email_cc(self):
        sender_user = mail_new_test_user(
            self.env,
            login="sender-test",
            groups="base.group_partner_manager,base.group_user",
            partner_id=self.sender.id,
            email=self.sender.email,
            name="Sender User Test",
        )
        # pylint: disable=C8107
        message = self.recipient.with_user(sender_user).message_post(
            body="<p>This is a test message</p>",
            email_cc="Dominique Pinon <unnamed@test.com>, sender@example.com",
        )
        # suggested recipients
        recipients = self.recipient._message_get_suggested_recipients()
        suggested_mails = {recipient["email"] for recipient in recipients}
        self.assertIn("unnamed@test.com", suggested_mails)
        self.assertEqual(len(recipients), 3)
        # Repeated Cc recipients
        message = self.env["mail.message"].create(
            {
                "subject": "Message test",
                "author_id": self.sender.id,
                "email_from": self.sender.email,
                "message_type": "comment",
                "model": "res.partner",
                "res_id": self.recipient.id,
                "partner_ids": [Command.link(self.recipient.id)],
                "email_cc": "Dominique Pinon <unnamed@test.com>, sender@example.com"
                ", recipient@example.com",
                "body": "<p>This is another test message</p>",
            }
        )
        if message._is_thread_message():
            with self.mock_smtplib_connection():
                self.env[message.model].browse(message.res_id).with_context(
                    mail_notify_force_send=True
                )._notify_thread(message)
        recipients = self.recipient._message_get_suggested_recipients()
        self.assertEqual(len(recipients), 3)
        self._check_partner_trackings_cc(message)

    def _check_partner_trackings_to(self, message):
        message_dict = Store().add(message).get_result()
        partner_trackings = message_dict["mail.message"][0]["partner_trackings"]
        self.assertEqual(len(partner_trackings), 4)
        # mail cc
        foundPartner = False
        foundNoPartner = False
        for tracking in partner_trackings:
            if tracking["partner_id"] == self.sender.id:
                foundPartner = True
            elif tracking["recipient"] == "support+unnamed@test.com":
                foundNoPartner = True
                self.assertFalse(tracking["partner_id"])
        self.assertTrue(foundPartner)
        self.assertTrue(foundNoPartner)

    def test_email_to(self):
        sender_user = mail_new_test_user(
            self.env,
            login="sender-test",
            groups="base.group_partner_manager,base.group_user",
            partner_id=self.sender.id,
            email=self.sender.email,
            name="Sender User Test",
        )
        # pylint: disable=C8107
        message = self.recipient.with_user(sender_user).message_post(
            body="<p>This is a test message</p>",
            email_to="Dominique Pinon <support+unnamed@test.com>, sender@example.com",
        )
        # suggested recipients
        recipients = self.recipient._message_get_suggested_recipients()
        suggested_mails = {recipient["email"] for recipient in recipients}
        self.assertIn("support+unnamed@test.com", suggested_mails)
        self.assertEqual(len(recipients), 3)
        # Repeated To recipients
        message = self.env["mail.message"].create(
            {
                "subject": "Message test",
                "author_id": self.sender.id,
                "email_from": self.sender.email,
                "message_type": "comment",
                "model": "res.partner",
                "res_id": self.recipient.id,
                "partner_ids": [Command.link(self.recipient.id)],
                "email_to": "Dominique Pinon <support+unnamed@test.com>"
                ", sender@example.com, recipient@example.com"
                ", TheCatchall@test.com",
                "body": "<p>This is another test message</p>",
            }
        )
        if message._is_thread_message():
            with self.mock_smtplib_connection():
                self.env[message.model].browse(message.res_id)._notify_thread(message)
        recipients = self.recipient._message_get_suggested_recipients()
        self.assertEqual(len(recipients), 4)
        self._check_partner_trackings_to(message)
        # Catchall + Alias
        alias_domain_id = self.env["mail.alias.domain"].create(
            {"catchall_alias": "TheCatchall", "name": "test.com"}
        )
        self.env["mail.alias"].create(
            {
                "alias_model_id": self.env["ir.model"]._get("res.partner").id,
                "alias_name": "support+unnamed",
                "alias_domain_id": alias_domain_id.id,
            }
        )
        recipients = self.recipient._message_get_suggested_recipients()
        self.assertEqual(len(recipients), 2)
        suggested_mails = {recipient["email"] for recipient in recipients}
        self.assertNotIn("support+unnamed@test.com", suggested_mails)

    def test_failed_message(self):
        MailMessageObj = self.env["mail.message"]
        # Create message
        mail, tracking = self.mail_send(self.recipient.email)
        self.assertFalse(tracking.mail_message_id.mail_tracking_needs_action)
        # Force error state
        tracking.state = "error"
        self.assertTrue(tracking.mail_message_id.mail_tracking_needs_action)
        failed_count = MailMessageObj.get_failed_count()
        self.assertTrue(failed_count > 0)
        values = tracking.mail_message_id.get_failed_messages()
        self.assertEqual(values[0]["id"], tracking.mail_message_id.id)
        messages = MailMessageObj.search([])
        messages_failed = MailMessageObj.search([["is_failed_message", "=", True]])
        self.assertTrue(messages)
        self.assertTrue(messages_failed)
        self.assertTrue(len(messages) > len(messages_failed))
        tracking.mail_message_id.set_need_action_done()
        self.assertFalse(tracking.mail_message_id.mail_tracking_needs_action)
        self.assertTrue(MailMessageObj.get_failed_count() < failed_count)
        # No author_id
        tracking.mail_message_id.author_id = False
        values = tracking.mail_message_id.get_failed_messages()[0]
        if values and values.get("author"):
            self.assertEqual(values["author"][0], -1)

    def test_init_messaging(self):
        _mail, tracking = self.mail_send(self.recipient.email)
        tracking.state = "error"

        store = Store()
        self.env.user._init_messaging(store)

        result = store.get_result()["Store"]
        self.assertEqual(
            result["failed"],
            {
                "id": "failed",
                "model": "mail.box",
                "counter": self.env["mail.message"].get_failed_count(),
            },
        )

    def mail_send(self, recipient):
        mail = self.env["mail.mail"].create(
            {
                "subject": "Test subject",
                "email_from": "from@domain.com",
                "email_to": recipient,
                "body_html": "<p>This is a test message</p>",
            }
        )
        with self.mock_smtplib_connection():
            mail.send()
        # Search tracking created
        tracking_email = self.env["mail.tracking.email"].search(
            [("mail_id", "=", mail.id)]
        )
        return mail, tracking_email

    @mute_logger("odoo.addons.mail_tracking.controllers.main")
    def test_mail_send(self):
        controller = MailTrackingController()
        db = self.env.cr.dbname
        image = base64.b64decode(BLANK)
        mail, tracking = self.mail_send(self.recipient.email)
        self.assertEqual(mail.email_to, tracking.recipient)
        self.assertEqual(mail.email_from, tracking.sender)
        with patch("odoo.http.db_filter") as mock_client:
            mock_client.return_value = True
            res = controller.mail_tracking_open(db, tracking.id, tracking.token)
            self.assertEqual(image, res.response[0])
            # Two events: sent and open
            self.assertEqual(2, len(tracking.tracking_event_ids))
            # Fake event: tracking_email_id = False
            res = controller.mail_tracking_open(db, False, False)
            self.assertEqual(image, res.response[0])
            # Two events again because no tracking_email_id found for False
            self.assertEqual(2, len(tracking.tracking_event_ids))

    @mute_logger("odoo.addons.mail_tracking.controllers.main")
    def test_mail_tracking_open(self):
        def mock_error_function(*args, **kwargs):
            raise Exception()

        controller = MailTrackingController()
        db = self.env.cr.dbname
        with patch("odoo.http.db_filter") as mock_client:
            mock_client.return_value = True
            mail, tracking = self.mail_send(self.recipient.email)
            # Tracking is in sent or delivered state. But no token give.
            # Don't generates tracking event
            controller.mail_tracking_open(db, tracking.id)
            self.assertEqual(1, len(tracking.tracking_event_ids))
            tracking.write({"state": "opened"})
            # Tracking isn't in sent or delivered state.
            # Don't generates tracking event
            controller.mail_tracking_open(db, tracking.id, tracking.token)
            self.assertEqual(1, len(tracking.tracking_event_ids))
            tracking.write({"state": "sent"})
            # Tracking is in sent or delivered state and a token is given.
            # Generates tracking event
            controller.mail_tracking_open(db, tracking.id, tracking.token)
            self.assertEqual(2, len(tracking.tracking_event_ids))
            # Generate new email due concurrent event filter
            mail, tracking = self.mail_send(self.recipient.email)
            tracking.write({"token": False})
            # Tracking is in sent or delivered state but a token is given for a
            # record that doesn't have a token.
            # Don't generates tracking event
            controller.mail_tracking_open(db, tracking.id, "tokentest")
            self.assertEqual(1, len(tracking.tracking_event_ids))
            # Tracking is in sent or delivered state and not token is given for
            # a record that doesn't have a token.
            # Generates tracking event
            controller.mail_tracking_open(db, tracking.id, False)
            self.assertEqual(2, len(tracking.tracking_event_ids))
            # Purposely trigger an error during mail_tracking_open
            # flow (to increase coverage)
            with patch(
                "odoo.addons.mail_tracking.models.mail_tracking_email.MailTrackingEmail.search",
                wraps=mock_error_function,
            ):
                controller.mail_tracking_open(db, tracking.id, False)
        # Purposely trigger an error during db_env (to increase coverage)
        with patch("odoo.http.db_filter") as mock_client, self.assertRaises(BadRequest):
            mock_client.return_value = False
            controller.mail_tracking_open(db, tracking.id, False)

    @mute_logger("odoo.addons.mail_tracking.controllers.main")
    def test_db_env(self):
        dbname = self.env.cr.dbname

        with patch("odoo.http.db_filter", return_value=False):
            with self.assertRaises(BadRequest):
                with db_env(dbname):
                    pass

        with patch("odoo.http.db_filter", return_value=True):
            with db_env(dbname) as env:
                self.assertEqual(env.cr, self.env.cr)

        mock_connection = Mock()
        mock_connection.cursor.return_value = self.env.cr
        with (
            patch("odoo.http.db_filter", return_value=True),
            patch.object(http.request, "db", f"{dbname}_other"),
            patch(
                "odoo.sql_db.db_connect", return_value=mock_connection
            ) as mock_connect,
        ):
            with db_env(dbname) as env:
                self.assertEqual(env.cr, self.env.cr)
            mock_connect.assert_called_once_with(dbname)
            mock_connection.cursor.assert_called_once_with()

        mock_connection = Mock()
        mock_connection.cursor.return_value = self.env.cr
        with (
            patch("odoo.http.db_filter", return_value=True),
            patch.object(http.request, "env", Mock(cr=None)),
            patch(
                "odoo.sql_db.db_connect", return_value=mock_connection
            ) as mock_connect,
        ):
            with db_env(dbname) as env:
                self.assertEqual(env.cr, self.env.cr)
            mock_connect.assert_called_once_with(dbname)
            mock_connection.cursor.assert_called_once_with()

    def test_concurrent_open(self):
        mail, tracking = self.mail_send(self.recipient.email)
        ts = time.time()
        metadata = {
            "ip": "127.0.0.1",
            "user_agent": "Odoo Test/1.0",
            "os_family": "linux",
            "ua_family": "odoo",
            "timestamp": ts,
        }
        # First open event
        tracking.event_create("open", metadata)
        opens = tracking.tracking_event_ids.filtered(lambda r: r.event_type == "open")
        self.assertEqual(len(opens), 1)
        # Concurrent open event
        metadata["timestamp"] = ts + 2
        tracking.event_create("open", metadata)
        opens = tracking.tracking_event_ids.filtered(lambda r: r.event_type == "open")
        self.assertEqual(len(opens), 1)
        # Second open event
        metadata["timestamp"] = ts + 350
        tracking.event_create("open", metadata)
        opens = tracking.tracking_event_ids.filtered(lambda r: r.event_type == "open")
        self.assertEqual(len(opens), 2)

    def test_concurrent_click(self):
        mail, tracking = self.mail_send(self.recipient.email)
        ts = time.time()
        metadata = {
            "ip": "127.0.0.1",
            "user_agent": "Odoo Test/1.0",
            "os_family": "linux",
            "ua_family": "odoo",
            "timestamp": ts,
            "url": "https://www.example.com/route/1",
        }
        # First click event (URL 1)
        tracking.event_create("click", metadata)
        opens = tracking.tracking_event_ids.filtered(lambda r: r.event_type == "click")
        self.assertEqual(len(opens), 1)
        # Concurrent click event (URL 1)
        metadata["timestamp"] = ts + 2
        tracking.event_create("click", metadata)
        opens = tracking.tracking_event_ids.filtered(lambda r: r.event_type == "click")
        self.assertEqual(len(opens), 1)
        # Second click event (URL 1)
        metadata["timestamp"] = ts + 350
        tracking.event_create("click", metadata)
        opens = tracking.tracking_event_ids.filtered(lambda r: r.event_type == "click")
        self.assertEqual(len(opens), 2)
        # Concurrent click event (URL 2)
        metadata["timestamp"] = ts + 2
        metadata["url"] = "https://www.example.com/route/2"
        tracking.event_create("click", metadata)
        opens = tracking.tracking_event_ids.filtered(lambda r: r.event_type == "click")
        self.assertEqual(len(opens), 3)

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_smtp_error(self):
        with patch(mock_send_email) as mock_func:
            mock_func.side_effect = Warning("Test error")
            mail, tracking = self.mail_send(self.recipient.email)
            self.assertEqual("error", tracking.state)
            self.assertEqual("Warning", tracking.error_type)
            self.assertEqual("Test error", tracking.error_description)
            self.assertTrue(self.recipient.email_bounced)

    def test_partner_email_change(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("open", {})
        orig_score = self.recipient.email_score
        orig_count = self.recipient.tracking_emails_count
        orig_email = self.recipient.email
        self.recipient.email = orig_email + "2"
        self.assertEqual(50.0, self.recipient.email_score)
        self.assertEqual(0, self.recipient.tracking_emails_count)
        self.recipient.email = orig_email
        self.assertEqual(orig_score, self.recipient.email_score)
        self.assertEqual(orig_count, self.recipient.tracking_emails_count)

    def test_process_hard_bounce(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("hard_bounce", {})
        self.assertEqual("bounced", tracking.state)
        self.assertTrue(self.recipient.email_score < 50.0)

    def test_process_soft_bounce(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("soft_bounce", {})
        self.assertEqual("soft-bounced", tracking.state)
        self.assertTrue(self.recipient.email_score < 50.0)

    def test_process_delivered(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("delivered", {})
        self.assertEqual("delivered", tracking.state)
        self.assertTrue(self.recipient.email_score > 50.0)

    def test_process_deferral(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("deferral", {})
        self.assertEqual("deferred", tracking.state)

    def test_process_spam(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("spam", {})
        self.assertEqual("spam", tracking.state)
        self.assertTrue(self.recipient.email_score < 50.0)

    def test_process_unsub(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("unsub", {})
        self.assertEqual("unsub", tracking.state)
        self.assertTrue(self.recipient.email_score < 50.0)

    def test_process_reject(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("reject", {})
        self.assertEqual("rejected", tracking.state)
        self.assertTrue(self.recipient.email_score < 50.0)

    def test_process_open(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("open", {})
        self.assertEqual("opened", tracking.state)
        self.assertTrue(self.recipient.email_score > 50.0)

    def test_process_click(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("click", {})
        self.assertEqual("opened", tracking.state)
        self.assertTrue(self.recipient.email_score > 50.0)

    def test_process_several_bounce(self):
        for _i in range(1, 10):
            mail, tracking = self.mail_send(self.recipient.email)
            tracking.event_create("hard_bounce", {})
            self.assertEqual("bounced", tracking.state)
        self.assertEqual(0.0, self.recipient.email_score)

    def test_bounce_new_partner(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("hard_bounce", {})
        new_partner = self.env["res.partner"].create({"name": "Test New Partner"})
        new_partner.email = self.recipient.email
        self.assertTrue(new_partner.email_bounced)

    def test_recordset_email_score(self):
        """For backwords compatibility sake"""
        trackings = self.env["mail.tracking.email"]
        for _i in range(11):
            mail, tracking = self.mail_send(self.recipient.email)
            tracking.event_create("click", {})
            trackings |= tracking
        self.assertEqual(100.0, trackings.email_score())

    def test_bounce_tracking_event_created(self):
        mail, tracking = self.mail_send(self.recipient.email)
        discuss_channel = self.env["discuss.channel"].create({"name": "Test Channel"})
        message = self.env["mail.message"].create(
            {
                "model": "discuss.channel",
                "res_id": discuss_channel.id,
                "body": "<p>This is a test message</p>",
                "message_type": "comment",
                "subtype_id": self.env.ref("mail.mt_comment").id,
                "author_id": self.sender.id,
                "date": fields.Datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        )
        message.mail_tracking_ids = [Command.link(tracking.id)]
        mail.mail_message_id = message
        message_dict = {
            "bounced_email": self.recipient.email,
            "bounced_message": message,
            "bounced_msg_ids": [message.message_id],
            "bounced_partner": self.recipient,
            "cc": "",
            "date": "2023-02-07 12:35:53",
            "email_from": "MAILER-DAEMON@eu-west-1.amazonses.com",
            "from": "MAILER-DAEMON@eu-west-1.amazonses.com",
            "in_reply_to": "<010201864d109aa7-west-1.amazonses.com>",
            "is_internal": False,
            "message_id": "<010201862be01f29-west-1.amazonses.com>",
            "message_type": "email",
            "parent_id": 15894917,
            "partner_ids": [],
            "recipients": "bounce+694942@recipient.net",
            "references": "<010201862bdfa5e9-west-1.amazonses.com>",
            "subject": "bounce notification",
            "to": "bounce+694942-mailing.contact-836@test.net",
        }
        self.env["mail.thread"]._routing_handle_bounce(message, message_dict)
        self.assertTrue(
            "soft_bounce"
            in message.mail_tracking_ids.tracking_event_ids.mapped("event_type")
        )

    def test_tracking_img_tag(self):
        mail_server = self.env["ir.mail_server"].create(
            {
                "name": "Tracking image SMTP",
                "smtp_host": "smtp.tracking.test",
            }
        )
        _mail, tracking = self.mail_send(self.recipient.email)
        body = f"<div>Body</div>{tracking._get_mail_tracking_img()}"

        def _html_body(email_message):
            html_part = email_message.get_body(preferencelist=("html",))
            self.assertTrue(html_part)
            return html_part.get_content()

        self.env["ir.config_parameter"].set_param(
            "mail_tracking.tracking_img_disabled", False
        )
        message = mail_server._build_email__(
            email_from="from@example.com",
            email_to="to@example.com",
            subject="Tracking enabled",
            body=body,
            subtype="html",
        )
        self.assertEqual(message["X-Odoo-MailTracking-ID"], str(tracking.id))
        self.assertIn("data-odoo-tracking-email", _html_body(message))

        self.env["ir.config_parameter"].set_param(
            "mail_tracking.tracking_img_disabled", True
        )
        message = mail_server._build_email__(
            email_from="from@example.com",
            email_to="to@example.com",
            subject="Tracking disabled",
            body=body,
            subtype="html",
        )
        self.assertEqual(message["X-Odoo-MailTracking-ID"], str(tracking.id))
        self.assertNotIn("data-odoo-tracking-email", _html_body(message))

    def test_search_is_failed_message(self):
        user_employee_1 = mail_new_test_user(
            self.env,
            groups="base.group_user",
            login="employee1",
            name="employee_1",
        )
        partner_employee = user_employee_1.partner_id
        user_employee_2 = mail_new_test_user(
            self.env,
            groups="base.group_user",
            login="employee2",
            name="employee_2",
        )
        message = self.env["mail.message"].create(
            {
                "subject": "Message test",
                "author_id": self.sender.id,
                "email_from": self.sender.email,
                "message_type": "comment",
                "model": "res.partner",
                "res_id": partner_employee.id,
                "partner_ids": [Command.link(partner_employee.id)],
                "body": "<p>This is a test message</p>",
            }
        )
        if message._is_thread_message():
            with self.mock_smtplib_connection():
                self.env[message.model].browse(message.res_id).with_context(
                    mail_notify_force_send=True
                )._notify_thread(message)
        # Search tracking created
        tracking_email = self.env["mail.tracking.email"].search(
            [
                ("mail_message_id", "=", message.id),
                ("partner_id", "=", partner_employee.id),
            ]
        )
        # Force error state
        tracking_email.state = "error"

        # employee_1 should read/search failed msg
        failed_msg = message.with_user(user_employee_1).read(
            fields=["is_failed_message"]
        )
        self.assertTrue(failed_msg[0]["is_failed_message"])
        self.assertTrue(
            self.env["mail.message"]
            .with_user(user_employee_1)
            .search(
                [
                    ("is_failed_message", "=", True),
                ]
            )
        )
        self.assertFalse(
            self.env["mail.message"]
            .with_user(user_employee_2)
            .search(
                [
                    ("is_failed_message", "=", True),
                ]
            )
        )

    def test_ir_mail_server_internal_helpers(self):
        mail_server = self.env["ir.mail_server"].create(
            {
                "name": "Coverage SMTP",
                "smtp_host": "smtp.coverage.test",
            }
        )
        self.assertEqual(
            mail_server._smtp_server_get(mail_server.id, False),
            "smtp.coverage.test",
        )

        _mail, tracking = self.mail_send(self.recipient.email)
        tracking_tag = (
            f'<img src="https://example.com/blank.gif" '
            f'data-odoo-tracking-email="{tracking.id}"/>'
        )
        body = f"<div>Body</div>{tracking_tag}"
        self.assertNotIn(
            "data-odoo-tracking-email",
            mail_server._tracking_img_remove(body),
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "mail_tracking.tracking_img_disabled", True
        )
        built_message = mail_server._build_email__(
            email_from="from@example.com",
            email_to="to@example.com",
            subject="Coverage",
            body=body,
            subtype="html",
        )
        self.assertEqual(
            built_message["X-Odoo-MailTracking-ID"],
            str(tracking.id),
        )
        self.assertNotIn("data-odoo-tracking-email", built_message.as_string())

    def test_get_failed_messsage_info(self):
        message = self.env["mail.message"].create(
            {
                "subject": "Coverage Message",
                "author_id": self.sender.id,
                "email_from": self.sender.email,
                "message_type": "comment",
                "model": "res.partner",
                "res_id": self.recipient.id,
                "subtype_id": self.env.ref("mail.mt_comment").id,
                "body": "<p>Coverage body</p>",
            }
        )
        tracking = self.env["mail.tracking.email"].create(
            {
                "mail_message_id": message.id,
                "partner_id": self.recipient.id,
                "recipient": self.recipient.email,
                "sender": self.sender.email,
            }
        )
        tracking.write({"state": "error"})

        values = self.env["mail.message"].get_failed_messsage_info(
            self.recipient.id,
            "res.partner",
        )
        self.assertTrue(values)
        self.assertEqual(values[0]["id"], message.id)

    def test_mail_tracking_email_helper_branches(self):
        message_with_subtype = self.env["mail.message"].create(
            {
                "subject": "Coverage Message Subtype",
                "author_id": self.sender.id,
                "email_from": self.sender.email,
                "message_type": "comment",
                "model": "res.partner",
                "res_id": self.recipient.id,
                "subtype_id": self.env.ref("mail.mt_comment").id,
                "body": "<p>Coverage body</p>",
            }
        )
        tracking_with_subtype = self.env["mail.tracking.email"].create(
            {
                "mail_message_id": message_with_subtype.id,
                "partner_id": self.recipient.id,
                "recipient": self.recipient.email,
                "sender": self.sender.email,
            }
        )
        self.assertEqual(
            tracking_with_subtype.message_id,
            message_with_subtype.message_id,
        )

        tracking_with_subtype.sudo().write({"token": False})
        tracking_image = tracking_with_subtype._get_mail_tracking_img()
        self.assertIn(
            (
                f"mail/tracking/open/{self.env.cr.dbname}/"
                f"{tracking_with_subtype.id}/blank.gif"
            ),
            tracking_image,
        )

        self.assertFalse(tracking_with_subtype._event_prepare("unknown_event", {}))
        with patch.object(
            type(message_with_subtype),
            "write",
            autospec=True,
            return_value=True,
        ) as mock_write:
            tracking_with_subtype._message_partners_check({}, "message-id-1")
        self.assertIn("notified_partner_ids", mock_write.call_args.args[1])

        message_without_subtype = self.env["mail.message"].create(
            {
                "subject": "Coverage Message No Subtype",
                "author_id": self.sender.id,
                "email_from": self.sender.email,
                "message_type": "email",
                "model": "res.partner",
                "res_id": self.recipient.id,
                "subtype_id": False,
                "body": "<p>Coverage body</p>",
            }
        )
        message_without_subtype.sudo().write({"subtype_id": False})
        self.assertFalse(message_without_subtype.subtype_id)
        tracking_without_subtype = self.env["mail.tracking.email"].create(
            {
                "mail_message_id": message_without_subtype.id,
                "partner_id": self.recipient.id,
                "recipient": self.recipient.email,
                "sender": self.sender.email,
            }
        )
        with patch.object(
            type(message_without_subtype),
            "write",
            autospec=True,
            return_value=True,
        ) as mock_write:
            tracking_without_subtype._message_partners_check({}, "message-id-2")
        self.assertIn("partner_ids", mock_write.call_args.args[1])

        _mail, tracking_with_mail = self.mail_send(self.recipient.email)
        admin_user = self.env.ref("base.user_admin")
        allowed_ids = (
            self.env["mail.tracking.email"]
            .with_user(admin_user)
            ._get_allowed_ids([tracking_with_mail.id])
        )
        self.assertIn(tracking_with_mail.id, allowed_ids)

    def test_mail_tracking_email_access_helpers(self):
        _mail, tracking = self.mail_send(self.recipient.email)

        with patch.object(
            type(tracking),
            "_get_allowed_ids",
            return_value=tracking.ids,
        ):
            self.assertFalse(tracking._get_forbidden_access())

        with patch.object(type(tracking), "_get_allowed_ids", return_value=[]):
            forbidden = tracking._get_forbidden_access()
        self.assertEqual(forbidden, tracking)

        def passthrough():
            return None

        with (
            patch(
                "odoo.orm.models.Model._check_access",
                return_value=(self.env["mail.tracking.email"], passthrough),
            ),
            patch.object(
                type(tracking),
                "_get_forbidden_access",
                return_value=tracking,
            ),
        ):
            result = tracking._check_access("read")
        self.assertEqual(result[0], tracking)
        self.assertIs(result[1], passthrough)

        with patch("odoo.orm.models.Model._check_access", return_value=None):
            self.assertIsNone(self.env["mail.tracking.email"]._check_access("read"))

        with (
            patch("odoo.orm.models.Model._check_access", return_value=None),
            patch.object(
                type(tracking),
                "_get_forbidden_access",
                return_value=tracking,
            ),
        ):
            result = tracking._check_access("read")
        self.assertEqual(result[0], tracking)
        self.assertIsInstance(result[1](), AccessError)

        with patch.object(
            type(tracking),
            "check_access",
            autospec=True,
        ) as mock_check_access:
            tracking.read(["id"])
        self.assertGreaterEqual(mock_check_access.call_count, 1)
        mock_check_access.assert_any_call(tracking, "read")

    def test_mail_tracking_event_and_gc_edge_cases(self):
        _mail, tracking = self.mail_send(self.recipient.email)

        event = self.env["mail.tracking.event"].create(
            {
                "tracking_email_id": tracking.id,
                "event_type": "open",
                "timestamp": time.time(),
            }
        )
        self.assertFalse(event.recipient_address)

        vals = self.env["mail.tracking.event"].process_sent(tracking, {})
        self.assertEqual(vals["event_type"], "sent")
        self.assertEqual(vals["tracking_email_id"], tracking.id)

        self.env["ir.config_parameter"].sudo().set_param(
            "mail_tracking.mail_tracking_email_max_age_days", "not-an-integer"
        )
        self.assertFalse(
            self.env["mail.tracking.email"]._gc_mail_tracking_email(limit=1)
        )

    def test_tracking_count_hidden_for_non_system_user(self):
        user_employee = mail_new_test_user(
            self.env,
            groups="base.group_user",
            login="coverage-employee",
            name="Coverage employee",
        )
        self.mail_send(self.recipient.email)
        self.assertEqual(
            self.recipient.with_user(user_employee).tracking_emails_count,
            0,
        )


@tagged("-at_install", "post_install")
class TestAccessTrackingEmail(HttpCaseWithUserDemo, TestMailTracking):
    patch_http_request = False

    def _get_tracking_email(
        self, user=SUPERUSER_ID, mail_msg_id=False, mail_id=False, partner_id=False
    ):
        domain = []
        if mail_msg_id:
            domain.append(("mail_message_id", "=", mail_msg_id))
        if mail_id:
            domain.append(("mail_id", "=", mail_id))
        if partner_id:
            domain.append(("partner_id", "=", partner_id))
        result = self.env["mail.tracking.email"].with_user(user).search(domain)
        return result

    def _create_failed_message_for_user(self, user):
        message = self.env["mail.message"].create(
            {
                "subject": f"Confidential Message for {user.name}",
                "body": "Confidential message",
                "author_id": user.partner_id.id,
                "email_from": user.email,
                "message_type": "comment",
                "model": "res.partner",
                "res_id": self.recipient.id,
                "partner_ids": [Command.link(self.recipient.id)],
            }
        )
        if message._is_thread_message():
            with self.mock_smtplib_connection():
                self.env[message.model].browse(message.res_id).with_context(
                    mail_notify_force_send=True
                )._notify_thread(message)
        tracking_email = self._get_tracking_email(
            mail_msg_id=message.id,
            partner_id=self.recipient.id,
        )
        self.assertTrue(tracking_email)
        tracking_email.state = "error"
        return message

    def test_access_tracking_email(self):
        if "hr.employee" in self.env:
            self.admin_user = self.env.ref("base.user_admin")
            user_employee_1 = mail_new_test_user(
                self.env,
                groups="base.group_user",
                login="employee1",
                name="employee 1",
            )
            employee_1 = self.env["hr.employee"].create(
                [
                    {
                        "name": "employee 1",
                        "user_id": user_employee_1.id,
                    },
                ]
            )
            user_employee_2 = mail_new_test_user(
                self.env,
                groups="base.group_user",
                login="employee2",
                name="employee 2",
            )

            # Create message
            message = self.env["mail.message"].create(
                {
                    "subject": "Confidential Message",
                    "body": "Confidential message",
                    "author_id": self.sender.id,
                    "email_from": self.sender.email,
                    "model": "hr.employee",
                    "res_id": employee_1.id,
                    "partner_ids": [(6, 0, [user_employee_1.partner_id.id])],
                }
            )
            if message._is_thread_message():
                with self.mock_smtplib_connection():
                    self.env[message.model].browse(message.res_id)._notify_thread(
                        message
                    )
            # Search tracking created
            tracking_email = self._get_tracking_email(
                mail_msg_id=message.id, partner_id=user_employee_1.partner_id.id
            )
            # ensure tracking exists
            self.assertTrue(tracking_email)
            # Addmin should be able to read/search the tracking email
            tracking_email.with_user(self.admin_user).read()
            self.assertTrue(
                self._get_tracking_email(
                    mail_msg_id=message.id,
                    partner_id=user_employee_1.partner_id.id,
                )
            )

            # employee 1 should be able to read/search the tracking email
            tracking_email.with_user(user_employee_1).read()
            self.assertTrue(
                self._get_tracking_email(
                    user=user_employee_1,
                    mail_msg_id=message.id,
                    partner_id=user_employee_1.partner_id.id,
                )
            )

            # employee 2 should not be able to read/search the tracking email
            with self.assertRaises(AccessError):
                tracking_email.with_user(user_employee_2).read()
            self.assertFalse(
                self._get_tracking_email(
                    user=user_employee_2,
                    mail_msg_id=message.id,
                    partner_id=user_employee_1.partner_id.id,
                )
            )

    def test_discuss_failed_messages_route(self):
        user_employee_1 = mail_new_test_user(
            self.env,
            login="failed_employee_1",
            password="failed_employee_1",
            groups="base.group_partner_manager,base.group_user",
            name="failed employee 1",
        )
        user_employee_2 = mail_new_test_user(
            self.env,
            login="failed_employee_2",
            password="failed_employee_2",
            groups="base.group_partner_manager,base.group_user",
            name="failed employee 2",
        )

        expected_message = self._create_failed_message_for_user(user_employee_1)
        other_message = self._create_failed_message_for_user(user_employee_2)

        self.authenticate(user=user_employee_1.login, password="failed_employee_1")
        result = self.make_jsonrpc_request("/mail/failed/messages")

        self.assertEqual(result["messages"], [expected_message.id])
        self.assertEqual(result["data"]["mail.message"][0]["id"], expected_message.id)
        self.assertNotIn(other_message.id, result["messages"])
