# Copyright 2019 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.mail.models.mail_thread import MailThread


class TestMailOptionalFollowernotifications(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_obj = cls.env["res.partner"]
        cls.partner_01 = cls.env.ref("base.res_partner_2")
        demo_user = cls.env.ref("base.user_demo")
        cls.partner_follower = demo_user.partner_id
        cls.partner_no_follower = demo_user.copy().partner_id
        cls.partner_no_follower.email = "test@example.com"
        cls.partner_01.message_subscribe(partner_ids=[cls.partner_follower.id])
        ctx = cls.env.context.copy()
        ctx.update(
            {
                "default_model": "res.partner",
                "default_res_ids": [cls.partner_01.id],
                "default_composition_mode": "comment",
            }
        )
        cls.mail_compose_context = ctx
        cls.MailCompose = cls.env["mail.compose.message"]

    def _send_mail(self, recipients, notify_followers):
        old_messages = self.env["mail.message"].search([])
        values = {
            "subject": "Your subject here",
            "body": "Your plain text body here",
            "partner_ids": [(6, 0, recipients.ids)],
            "notify_followers": notify_followers,
        }
        composer = self.MailCompose.with_context(**self.mail_compose_context).create(
            values
        )
        composer.action_send_mail()
        return self.env["mail.message"].search([]) - old_messages

    def test_1(self):
        """
        Data:
            One partner follower of partner_01
        Test case:
            Send message to the follower and a non follower partner
        Expected result:
            Both are notified
        """
        message = self._send_mail(
            self.partner_follower + self.partner_no_follower, notify_followers=True
        )
        self.assertEqual(
            message.notification_ids.mapped("res_partner_id"),
            self.partner_no_follower + self.partner_follower,
        )

    def test_2(self):
        """
        Data:
            One partner follower of partner_01
        Test case:
            Send message to the non follower partner
        Expected result:
            Both are notified
        """
        message = self._send_mail(self.partner_no_follower, notify_followers=True)
        self.assertEqual(
            message.notification_ids.mapped("res_partner_id"),
            self.partner_no_follower + self.partner_follower,
        )

    def test_3(self):
        """
        Data:
            One partner follower of partner_01
        Test case:
            Send message to the non follower partner and disable the
            notification to followers
        Expected result:
            Only the non follower partner is notified
        """
        message = self._send_mail(self.partner_no_follower, notify_followers=False)
        self.assertEqual(
            message.notification_ids.mapped("res_partner_id"), self.partner_no_follower
        )

    def test_4_explicit_non_follower_not_in_partner_ids_is_kept(self):
        """
        Data:
            One partner follower of partner_01, and another recipient
            never added to partner_ids, but flagged as is_follower=False.
        Test case:
            Send message to the non follower partner and disable the
            notification to followers.
        Expected result:
            The injected recipient is not a follower, so it must survive
            the notify_followers=False filter even though it is not in
            partner_ids. Only real followers should be stripped.
        Note:
            We are forced to patch because in core there is no way
            to get is_follower=False for someone who isn't in pids.
            However, this is interesting to test because it may happen
            in combination with other modules, like 'mail_composer_cc_bcc'.
        """
        extra_partner = self.partner_no_follower.copy()
        extra_partner.email = "extra@example.com"
        original = MailThread._notify_get_recipients

        def patched(self, message, msg_vals, **kwargs):
            rdata = original(self, message, msg_vals, **kwargs)
            rdata.append(
                {
                    "id": extra_partner.id,
                    "active": True,
                    "share": True,
                    "notif": "email",
                    "type": "customer",
                    "is_follower": False,
                    "lang": False,
                    "uid": False,
                }
            )
            return rdata

        with patch.object(MailThread, "_notify_get_recipients", patched):
            message = self._send_mail(self.partner_no_follower, notify_followers=False)

        self.assertIn(
            extra_partner,
            message.notification_ids.mapped("res_partner_id"),
            "An explicit non-follower recipient (not in partner_ids)"
            "must not be stripped when notify_followers=False",
        )
        self.assertNotIn(
            self.partner_follower,
            message.notification_ids.mapped("res_partner_id"),
            "A genuine follower must still be stripped when notify_followers=False",
        )
