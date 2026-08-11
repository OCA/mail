# Copyright 2024 Tecnativa - Carlos Lopez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import Form, RecordCapturer, tagged
from odoo.tests.common import HttpCase, users

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.test_mail_composer import TestMailComposer


@tagged("post_install", "-at_install")
class TestMailForward(TestMailComposer, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_test = mail_new_test_user(
            cls.env,
            login="user_test_forward",
            groups="base.group_user,base.group_partner_manager",
        )
        cls.test_record.write({"name": "Test Forward", "email": "test@example.com"})
        cls.partner_follower1 = cls.env["res.partner"].create(
            {"name": "Follower1", "email": "follower1@example.com"}
        )
        cls.partner_follower2 = cls.env["res.partner"].create(
            {"name": "Follower2", "email": "follower2@example.com"}
        )
        cls.partner_forward = cls.env["res.partner"].create(
            {"name": "Forward", "email": "forward@example.com"}
        )
        cls.env["ir.model"]._get("res.partner").enable_forward_to = True

    @users("user_test_forward")
    def test_01_mail_forward(self):
        """
        Send an email to followers
        and forward it to another partner.
        """
        ctx = {
            "default_model": self.test_record._name,
            "default_res_ids": [self.test_record.id],
        }
        composer_form = Form(self.env["mail.compose.message"].with_context(**ctx))
        composer_form.body = "<p>Hello</p>"
        composer_form.partner_ids.add(self.partner_follower1)
        composer_form.partner_ids.add(self.partner_follower2)
        composer = composer_form.save()
        with self.mock_mail_gateway():
            composer._action_send_mail()
        # Verify the followers of mail.message
        message = self.test_record.message_ids[0]
        self.assertEqual(len(message.notified_partner_ids), 2)
        self.assertIn(self.partner_follower1, message.notified_partner_ids)
        self.assertIn(self.partner_follower2, message.notified_partner_ids)
        self.assertNotIn(self.partner_forward, message.notified_partner_ids)
        self.assertNotIn("---------- Forwarded message ---------", message.body)
        # Forward the email
        # only the partner_forward should receive the email
        message_domain = [
            ("model", "=", self.test_record._name),
            ("res_id", "=", self.test_record.id),
        ]
        with RecordCapturer(self.env["mail.message"], message_domain) as capture:
            with self.mock_mail_gateway():
                self.start_tour(
                    "/web", "mail_forward.mail_forward_tour", login="user_test_forward"
                )
        # Verify the followers of mail.message
        forward_message = capture.records
        self.assertEqual(len(forward_message.notified_partner_ids), 1)
        self.assertNotIn(self.partner_follower1, forward_message.notified_partner_ids)
        self.assertIn(self.partner_forward, forward_message.notified_partner_ids)
        self.assertIn("---------- Forwarded message ---------", forward_message.body)

    @users("user_test_forward")
    def test_mail_forward_another_thread(self):
        """
        Check that the email is forwarded to another thread.
        and the email is sent to the followers of the another thread.
        """
        ctx = {
            "default_model": self.test_record._name,
            "default_res_ids": [self.test_record.id],
        }
        composer_form = Form(self.env["mail.compose.message"].with_context(**ctx))
        composer_form.body = "<p>Hello</p>"
        composer_form.subject = "Test Forward"
        composer_form.partner_ids.add(self.partner_follower1)
        composer = composer_form.save()
        with self.mock_mail_gateway():
            composer._action_send_mail()
        # Verify the followers of mail.message
        message = self.test_record.message_ids[0]
        self.assertEqual(len(message.notified_partner_ids), 1)
        self.assertIn(self.partner_follower1, message.notified_partner_ids)
        self.assertNotIn(self.partner_follower2, message.notified_partner_ids)
        self.assertNotIn(self.partner_forward, message.notified_partner_ids)
        self.assertNotIn("---------- Forwarded message ---------", message.body)
        # Forward the email to another record(self.partner_forward)
        message_domain = [
            ("model", "=", self.partner_forward._name),
            ("res_id", "=", self.partner_forward.id),
        ]
        with RecordCapturer(self.env["mail.message"], message_domain) as capture:
            with self.mock_mail_gateway():
                self.start_tour(
                    "/web",
                    "mail_forward.mail_another_thread_tour",
                    login="user_test_forward",
                )
        # Verify the followers of mail.message
        forward_message = capture.records
        self.assertEqual(forward_message.subject, "Fwd: Test Forward")
        self.assertEqual(len(forward_message.notified_partner_ids), 1)
        self.assertNotIn(self.partner_follower1, forward_message.notified_partner_ids)
        # the partner partner_follower2 is added to the message
        # but is not added as a follower automatically.
        self.assertIn(self.partner_follower2, forward_message.notified_partner_ids)
        self.assertNotIn(
            self.partner_follower2, self.partner_forward.message_partner_ids
        )
        self.assertIn("---------- Forwarded message ---------", forward_message.body)
