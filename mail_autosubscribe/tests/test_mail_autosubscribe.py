# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.orm.model_classes import add_to_registry
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestMailAutosubscribe(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        # Load fake order model
        from .models.fake_order import FakeOrder

        add_to_registry(cls.registry, FakeOrder)
        cls.registry._setup_models__(cls.env.cr, ["fake.order"])
        cls.registry.init_models(cls.env.cr, ["fake.order"], {"models_to_check": True})
        cls.addClassCleanup(cls.registry.__delitem__, "fake.order")
        cls.fake_order_model = cls.env["ir.model"].search(
            [("model", "=", "fake.order")]
        )
        # Email Template
        mail_template_model = cls.env["mail.template"].with_context(
            test_mail_autosubscribe=True
        )
        cls.mail_template = mail_template_model.create(
            {
                "model_id": cls.fake_order_model.id,
                "name": "Fake Order: Send by Mail",
                "subject": "Fake Order: {{object.partner_id.name}}",
                "partner_to": "{{object.partner_id.id}}",
                "body_html": "Hello, this is a fake order",
            }
        )
        # Partners - use test fixtures instead of demo data external IDs
        cls.commercial_partner = cls.env["res.partner"].create(
            {"name": "Commercial Partner"}
        )
        cls.partner_1 = cls.env["res.partner"].create(
            {"name": "Partner 1", "parent_id": cls.commercial_partner.id}
        )
        cls.partner_2 = cls.env["res.partner"].create(
            {"name": "Partner 2", "parent_id": cls.commercial_partner.id}
        )
        cls.partner_3 = cls.env["res.partner"].create(
            {"name": "Partner 3", "parent_id": cls.commercial_partner.id}
        )
        # Autosubscribe rules
        cls.autosubscribe_fake_order = cls.env["mail.autosubscribe"].create(
            {"model_id": cls.fake_order_model.id}
        )
        cls.partner_3.mail_autosubscribe_ids = [(4, cls.autosubscribe_fake_order.id)]
        # Empty fake.order
        cls.order = cls.env["fake.order"].create({"partner_id": cls.partner_2.id})

    def test_message_subscribe(self):
        """Test autosubscribe on a basic workflow"""
        self.assertFalse(self.order.message_partner_ids, "No subscribers yet")
        self.order.message_subscribe([self.order.partner_id.id])
        self.assertEqual(
            self.order.message_partner_ids,
            self.partner_2 | self.partner_3,
            "Partner 3 is automatically subscribed",
        )

    def test_message_subscribe_disabled(self):
        """Test autosubscribe on a basic workflow (disabled)"""
        self.partner_3.mail_autosubscribe_ids = [(5, False)]
        self.assertFalse(self.order.message_partner_ids, "No subscribers yet")
        self.order.message_subscribe([self.order.partner_id.id])
        self.assertEqual(
            self.order.message_partner_ids,
            self.partner_2,
            "Partner 2 is the only subscriber",
        )

    def test_mail_template(self):
        """Test autosubscribe when partner is set in the mail.template partners_to"""
        self.mail_template.send_mail(self.order.id)
        message = self.order.message_ids[0]
        self.assertEqual(message.partner_ids, self.partner_2 | self.partner_3)

    def test_mail_template_disabled(self):
        """Test autosubscribe when the partner is not an autosubscribe follower"""
        self.partner_3.mail_autosubscribe_ids = [(5, False)]
        self.mail_template.send_mail(self.order.id)
        message = self.order.message_ids[0]
        self.assertEqual(message.partner_ids, self.partner_2)

    def test_mail_template_no_autosubscribe_followers(self):
        """Test autosubscribe doesn't apply if it's disabled on the template"""
        self.mail_template.use_autosubscribe_followers = False
        self.mail_template.send_mail(self.order.id)
        message = self.order.message_ids[0]
        self.assertEqual(message.partner_ids, self.partner_2)

    def test_mail_template_default_recipients(self):
        """Test autosubscribe when using default recipients"""
        self.mail_template.use_default_to = True
        self.mail_template.send_mail(self.order.id)
        message = self.order.message_ids[0]
        self.assertEqual(message.partner_ids, self.partner_2 | self.partner_3)

    def test_mail_message_composer(self):
        """Test autosubscribe when using the mail composer"""
        self.assertFalse(self.order.message_partner_ids, "No subscribers yet")
        composer = Form(
            self.env["mail.compose.message"].with_context(
                default_model="fake.order",
                default_res_ids=[self.order.id],
                default_use_template=True,
                default_template_id=self.mail_template.id,
                default_composition_mode="comment",
            )
        )
        composer.save().action_send_mail()
        message = self.order.message_ids[0]
        self.assertEqual(message.partner_ids, self.partner_2 | self.partner_3)

    def test_mail_message_composer_no_autosubscribe_followers(self):
        """Test autosubscribe when using the mail composer and it's disabled"""
        self.mail_template.use_autosubscribe_followers = False
        composer = Form(
            self.env["mail.compose.message"].with_context(
                default_model="fake.order",
                default_res_ids=[self.order.id],
                default_use_template=True,
                default_template_id=self.mail_template.id,
                default_composition_mode="comment",
            )
        )
        composer.save().action_send_mail()
        message = self.order.message_ids[0]
        self.assertEqual(message.partner_ids, self.partner_2)
