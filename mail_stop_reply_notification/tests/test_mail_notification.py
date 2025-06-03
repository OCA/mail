# Copyright 2025 Aulora AG
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from email.utils import formatdate, make_msgid

from odoo.tests.common import TransactionCase


class TestMailNotification(TransactionCase):
    """
    Test cases for mail notification on a reply to a message
    on a partner.
    New partner have two users as followers and admin user
    writes a message on the partner.

    1st case:
    Follower users receive notifications by email.
    When the partner replies to the message
    from the admin user, the followers should not receive
    an email notification about the reply.

    2nd case:
    Follower users receive notifications in Odoo.
    When the partner replies to the message
    from the admin user, the followers should receive
    a notification about the reply.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.demo_user = cls.env.ref("base.user_demo")
        cls.admin_user = cls.env.ref("base.user_admin")

        cls.partner = cls.env["res.partner"].create(
            {"name": "Test partner", "email": "test.partner@example.com"}
        )
        # Set users as followers of the partner
        cls.partner.message_subscribe(
            [cls.demo_user.partner_id.id, cls.demo_user.partner_id.id]
        )

        # Admin user writes a message on the partner
        cls.message = cls.partner.message_post(
            body="This is a test message",
            author_id=cls.admin_user.partner_id.id,
        )
        # Prepare a reply message data
        cls.reply_message = f"""MIME-Version: 1.0
Date: {formatdate(localtime=True)}
Message-ID: {make_msgid()}
Subject: Reply Message
From: Test partner <test.partner@example.com>
To: {cls.admin_user.partner_id.email}
In-Reply-To: {cls.message.message_id}
References: {cls.message.message_id}
Content-Type: multipart/alternative; boundary="000000000000a47519057e029630"

--000000000000a47519057e029630
Content-Type: text/plain; charset="UTF-8"


--000000000000a47519057e029630
Content-Type: text/html; charset="UTF-8"
Content-Transfer-Encoding: quoted-printable

<div>Reply message</div>

--000000000000a47519057e029630--
"""

    def test_email_notification_on_reply(self):
        """
        Demo and Admin users receive notifications by email.
        The partner replies to the message from Admin user.
        The followers should not receive an email notification
        about the reply.
        """
        # Make sure users are notified by email
        self.demo_user.write(
            {
                "notification_type": "email",
            }
        )
        self.admin_user.write(
            {
                "notification_type": "email",
            }
        )
        # Partner replies to the message
        self.partner.message_process("res.partner", self.reply_message)
        reply_message = self.env["mail.message"].search(
            [
                ("model", "=", "res.partner"),
                ("res_id", "=", self.partner.id),
                ("id", ">", self.message.id),
                ("message_type", "=", "email"),
            ]
        )
        # Check that reply was created and linked to the partner
        self.assertTrue(reply_message, "Reply message should be processed")
        self.assertEqual(
            reply_message.model, "res.partner", "Reply should be linked to partner"
        )
        self.assertEqual(
            reply_message.res_id,
            self.partner.id,
            "Reply should be linked to the correct partner",
        )
        # Check that no email notifications were sent
        self.assertFalse(reply_message.notified_partner_ids, "Noone to be notified")
        self.assertFalse(
            reply_message.notification_ids, "Notifications should not be set"
        )

    def test_inbox_notification_on_reply(self):
        """
        Demo and Admin users receive notifications in Odoo.
        The partner replies to the message.
        The followers should receive a notification about the reply.
        """
        # Make sure users are notified by email
        self.demo_user.write(
            {
                "notification_type": "inbox",
            }
        )
        self.admin_user.write(
            {
                "notification_type": "inbox",
            }
        )
        # Partner replies to the message
        self.partner.message_process("res.partner", self.reply_message)
        reply_message = self.env["mail.message"].search(
            [
                ("model", "=", "res.partner"),
                ("res_id", "=", self.partner.id),
                ("id", ">", self.message.id),
                ("message_type", "=", "email"),
            ]
        )
        # Check that reply was created and linked to the partner
        self.assertTrue(reply_message, "Reply message should be processed")
        self.assertEqual(
            reply_message.model, "res.partner", "Reply should be linked to partner"
        )
        self.assertEqual(
            reply_message.res_id,
            self.partner.id,
            "Reply should be linked to the correct partner",
        )
        # Check that Odoo notifications were set
        self.assertTrue(
            reply_message.notified_partner_ids, "Followers should be notified"
        )
        self.assertTrue(reply_message.notification_ids, "Notifications should be set")
