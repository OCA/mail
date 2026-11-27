# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from email import message_from_string

from odoo.tests.common import TransactionCase, new_test_user

from .common import read_eml

REPLY_TEMPLATE = read_eml("reply.eml")


class TestIncomingMailNotification(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        partner_model = cls.env["res.partner"]
        cls.record = partner_model.create({"name": "Thread"})
        cls.sender = partner_model.create(
            {"name": "Sender", "email": "sender@example.com"}
        )
        cls.external = partner_model.create(
            {"name": "External", "email": "external@example.com"}
        )
        cls.internal_email = new_test_user(
            cls.env,
            login="internal_email",
            email="internal_email@example.com",
            groups="base.group_user",
            notification_type="email",
        ).partner_id
        cls.internal_inbox = new_test_user(
            cls.env,
            login="internal_inbox",
            groups="base.group_user",
            notification_type="inbox",
        ).partner_id
        cls.record.message_subscribe(
            partner_ids=(
                cls.sender | cls.external | cls.internal_email | cls.internal_inbox
            ).ids
        )
        cls.parent = cls.record.message_post(
            body="Hello",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )

    def _notified(self, message):
        return {
            notification.res_partner_id: notification.notification_type
            for notification in message.notification_ids
        }

    def _receive_reply(self):
        message_id = f"<{self._testMethodName}@example.com>"
        raw = REPLY_TEMPLATE.format(
            message_id=message_id, parent_id=self.parent.message_id
        )
        self.assertEqual(
            message_from_string(raw)["In-Reply-To"], self.parent.message_id
        )
        self.env["mail.thread"].message_process("res.partner", raw)
        reply = self.env["mail.message"].search([("message_id", "=", message_id)])
        self.assertEqual(reply.res_id, self.record.id)
        return self._notified(reply)

    def test_incoming_mail_not_forwarded_to_externals(self):
        notified = self._receive_reply()
        self.assertNotIn(self.external, notified)
        self.assertEqual(notified[self.internal_email], "email")
        self.assertEqual(notified[self.internal_inbox], "inbox")

    def test_incoming_mail_internal_email_disabled(self):
        self.env.company.notify_internal_on_incoming_email = False
        notified = self._receive_reply()
        self.assertNotIn(self.external, notified)
        self.assertNotIn(self.internal_email, notified)
        self.assertEqual(notified[self.internal_inbox], "inbox")

    def test_incoming_mail_forward_enabled(self):
        self.env.company.disable_incoming_mail_forward = False
        notified = self._receive_reply()
        self.assertEqual(notified[self.external], "email")

    def test_comment_still_sent_to_externals(self):
        notified = self._notified(self.parent)
        self.assertEqual(notified[self.external], "email")
        self.assertEqual(notified[self.internal_email], "email")
