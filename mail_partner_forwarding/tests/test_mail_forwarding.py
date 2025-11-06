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
