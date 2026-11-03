# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.orm.model_classes import add_to_registry
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestMailForwarding(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        from .models.fake_order import FakeOrder

        add_to_registry(cls.registry, FakeOrder)

        test_models = ["fake.order"]
        cls.registry._setup_models__(cls.env.cr, test_models)
        cls.registry.init_models(cls.env.cr, test_models, {"models_to_check": True})

        for model_name in test_models:
            cls.addClassCleanup(cls.registry.__delitem__, model_name)

        cls.fake_order_model = cls.env["ir.model"].search(
            [("model", "=", "fake.order")]
        )

        cls.partner_1 = cls.env["res.partner"].create(
            {
                "name": "Test Partner 1 (Forwarding)",
                "email": "partner1@test.example.com",
            }
        )
        cls.partner_2 = cls.env["res.partner"].create(
            {
                "name": "Test Partner 2 (Main)",
                "email": "partner2@test.example.com",
            }
        )

        cls.partner_2.forwarding_partner_id = cls.partner_1

        cls.order = cls.env["fake.order"].create({"partner_id": cls.partner_2.id})

    def _post(self, partners):
        return self.order.message_post(
            body=self.env._("Test"),
            message_type="comment",
            subtype_id=self.env.ref("mail.mt_comment").id,
            partner_ids=partners.ids,
        )

    def _notifications(self, message, partner):
        return message.notification_ids.filtered(lambda n: n.res_partner_id == partner)

    def test_message_post_forwarding(self):
        """The forwarding partner gets its own email notification"""
        message = self._post(self.partner_2)
        notif = self._notifications(message, self.partner_1)
        self.assertEqual(len(notif), 1)
        self.assertEqual(notif.notification_type, "email")
        self.assertNotEqual(notif.notification_status, "canceled")
        self.assertEqual(notif.mail_email_address, "partner1@test.example.com")
        self.assertEqual(len(self._notifications(message, self.partner_2)), 1)

    def test_message_post_forwarding_with_email_only_recipient(self):
        """Email-only recipients (no partner) do not break the forwarding"""
        message = self.order.message_post(
            body=self.env._("Test"),
            message_type="comment",
            subtype_id=self.env.ref("mail.mt_comment").id,
            partner_ids=self.partner_2.ids,
            outgoing_email_to="unknown@test.example.com",
        )
        self.assertEqual(len(self._notifications(message, self.partner_1)), 1)

    def test_message_post_forwarding_already_recipient(self):
        """No extra notification if the forwarding partner is already notified"""
        message = self._post(self.partner_2 | self.partner_1)
        self.assertEqual(len(self._notifications(message, self.partner_1)), 1)

    def test_message_post_without_forwarding(self):
        """Partners without forwarding partner do not forward anything"""
        message = self._post(self.partner_1)
        self.assertEqual(message.notification_ids.res_partner_id, self.partner_1)

    def test_message_post_forwarding_to_user_inbox(self):
        """The notification type follows the forwarding user preference"""
        user = new_test_user(
            self.env, login="forwarding_user", notification_type="inbox"
        )
        self.partner_2.forwarding_partner_id = user.partner_id
        message = self._post(self.partner_2)
        notif = self._notifications(message, user.partner_id)
        self.assertEqual(notif.notification_type, "inbox")

    def _post_note(self, partners):
        return self.order.message_post(
            body=self.env._("Internal note"),
            message_type="comment",
            subtype_id=self.env.ref("mail.mt_note").id,
            partner_ids=partners.ids,
        )

    def test_forwarding_data_is_the_forwarding_partner_one(self):
        """An external forwarding partner is notified as a customer"""
        user = new_test_user(self.env, login="internal_original")
        user.partner_id.forwarding_partner_id = self.partner_1
        message = self._post(user.partner_id)
        data = next(
            r
            for r in self.order._notify_get_recipients(message)
            if r["id"] == self.partner_1.id
        )
        self.assertEqual(data["type"], "customer")
        self.assertTrue(data["share"])
        self.assertFalse(data["uid"])
        self.assertEqual(data["email_normalized"], "partner1@test.example.com")

    def test_note_not_forwarded_to_external_partner(self):
        """Internal notes are not forwarded to external partners"""
        user = new_test_user(self.env, login="internal_note_original")
        user.partner_id.forwarding_partner_id = self.partner_1
        message = self._post_note(user.partner_id)
        self.assertFalse(self._notifications(message, self.partner_1))
        self.assertTrue(self._notifications(message, user.partner_id))

    def test_note_forwarded_to_internal_user(self):
        """Internal notes are forwarded to internal users"""
        user = new_test_user(self.env, login="internal_note_from")
        forwarding_user = new_test_user(
            self.env, login="internal_note_to", notification_type="inbox"
        )
        user.partner_id.forwarding_partner_id = forwarding_user.partner_id
        message = self._post_note(user.partner_id)
        notif = self._notifications(message, forwarding_user.partner_id)
        self.assertEqual(notif.notification_type, "inbox")

    def test_forwarding_keeps_user_partner(self):
        """Forwarding does not change the partner of the original user"""
        user = new_test_user(self.env, login="keeps_partner_user")
        forwarding_user = new_test_user(self.env, login="keeps_partner_fw")
        user.partner_id.forwarding_partner_id = forwarding_user.partner_id
        partner = user.partner_id
        self.env.invalidate_all()
        self._post(partner)
        self.assertEqual(user.partner_id, partner)
        self.assertEqual(forwarding_user.partner_id.user_ids, forwarding_user)

    def test_user_writes_own_forwarding_partner(self):
        """An internal user can set the forwarding partner on its own user"""
        user = new_test_user(self.env, login="own_forwarding_user")
        user.with_user(user).write({"forwarding_partner_id": self.partner_1.id})
        self.assertEqual(user.partner_id.forwarding_partner_id, self.partner_1)
        self.assertEqual(
            user.with_user(user).read(["forwarding_partner_id"])[0][
                "forwarding_partner_id"
            ][0],
            self.partner_1.id,
        )
