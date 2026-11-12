# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.orm.model_classes import add_to_registry
from odoo.tests.common import TransactionCase, tagged


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

    def test_message_post_forwarding(self):
        """Test forwarding when send a message for the user"""
        self.order.message_post(
            body=self.env._("Test"),
            message_type="comment",
            subtype_id=self.env.ref("mail.mt_comment").id,
            partner_ids=[self.partner_2.id],
        )

    def _create_internal_partner(self, login):
        user = self.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@test.example.com",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        return user.partner_id

    def _forwarded_recipients(
        self, original, forwarding, subtype_xmlid="mail.mt_comment"
    ):
        original.forwarding_partner_id = forwarding
        message = self.order.message_post(
            body=self.env._("Test"),
            message_type="comment",
            subtype_id=self.env.ref(subtype_xmlid).id,
            partner_ids=[original.id],
        )
        recipients = self.order._notify_get_recipients(
            message, {"partner_ids": [original.id]}
        )
        return {r["id"]: r for r in recipients}

    def test_external_forwards_to_internal(self):
        """The forwarded recipient has its own data, not the original's"""
        internal = self._create_internal_partner("internal_forwarding_user")
        self.assertTrue(self.partner_2.partner_share)
        by_id = self._forwarded_recipients(self.partner_2, internal)
        self.assertIn(internal.id, by_id)
        data = by_id[internal.id]
        self.assertFalse(data["share"])
        self.assertEqual(data["email_normalized"], internal.email_normalized)
        self.assertEqual(data["name"], internal.name)
        self.assertTrue(data["uid"])

    def test_internal_forwards_to_external(self):
        """An external forwarding partner is not given the internal data"""
        internal = self._create_internal_partner("internal_original_user")
        by_id = self._forwarded_recipients(internal, self.partner_1)
        self.assertIn(self.partner_1.id, by_id)
        data = by_id[self.partner_1.id]
        self.assertTrue(data["share"])
        self.assertEqual(data["email_normalized"], self.partner_1.email_normalized)
        self.assertEqual(data["name"], self.partner_1.name)
        self.assertFalse(data["uid"])

    def test_internal_message_not_forwarded_to_external(self):
        """Internal notes are not forwarded to external partners"""
        internal = self._create_internal_partner("internal_note_user")
        by_id = self._forwarded_recipients(
            internal, self.partner_1, subtype_xmlid="mail.mt_note"
        )
        self.assertNotIn(self.partner_1.id, by_id)
