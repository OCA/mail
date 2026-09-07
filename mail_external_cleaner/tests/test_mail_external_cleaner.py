# Copyright 2025 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo.orm.model_classes import add_to_registry

from odoo.addons.mail.tests.common import MailCommon


class TestMailExternalCleaner(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from .portal_fake_model import PortalFakeModel

        add_to_registry(cls.env.registry, PortalFakeModel)
        cls.registry._setup_models__(cls.env.cr, ["portal.fake.model"])
        cls.registry.init_models(
            cls.env.cr, ["portal.fake.model"], {"models_to_check": True}
        )
        cls.addClassCleanup(cls.registry.__delitem__, "portal.fake.model")

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Partner Test",
                "email": "partner_test@test.example.com",
                "company_id": cls.env.company.id,
            }
        )
        cls.portal = cls.env["portal.fake.model"].create(
            {
                "name": "Portal Test",
                "partner_id": cls.partner.id,
            }
        )
        cls.attachment = cls.env["ir.attachment"].create(
            {
                "name": "test.txt",
                "datas": base64.b64encode(b"test attachment data"),
                "mimetype": "text/plain",
            }
        )
        cls.url = (
            cls.env["ir.config_parameter"]
            .sudo()
            .get_param("web.base.url", default="http://localhost:8069")
        )

    def test_company_logo(self):
        image_src = f"{self.url}/logo.png?company={self.env.company.id}"
        with self.mock_mail_gateway():
            self.portal.with_context(mail_notify_force_send=True).message_post(
                body=f'<p>Checking <img src="{image_src}" alt="My Image"/></p>',
                subject="Test Email with External Image",
                partner_ids=self.partner.ids,
                attachments=[(self.attachment.name, self.attachment.datas)],
            )
        self.assertEqual(len(self._mails), 1)
        self.assertNotIn(self.url, self._mails[0]["body_alternative"])

    def test_image_attachment(self):
        image = self.env["ir.attachment"].create(
            {
                "name": "test_image.png",
                "datas": base64.b64encode(b"test image data"),
                "mimetype": "image/png",
            }
        )
        image_src = f"{self.url}/web/image/{image.id}"
        with self.mock_mail_gateway():
            self.portal.with_context(mail_notify_force_send=True).message_post(
                body=f'<p>Checking <img src="{image_src}" alt="My Image"/></p>',
                subject="Test Email with External Image",
                partner_ids=self.partner.ids,
                attachments=[(self.attachment.name, self.attachment.datas)],
            )
        self.assertEqual(len(self._mails), 1)
        self.assertNotIn(self.url, self._mails[0]["body_alternative"])

    def test_other_images(self):
        """Should not replace as we don't know how to handle them."""
        image_src = f"{self.url}/image.png"
        with self.mock_mail_gateway():
            self.portal.with_context(mail_notify_force_send=True).message_post(
                body=f'<p>Checking <img src="{image_src}" alt="My Image"/></p>',
                subject="Test Email with External Image",
                partner_ids=self.partner.ids,
                attachments=[(self.attachment.name, self.attachment.datas)],
            )
        self.assertEqual(len(self._mails), 1)
        self.assertIn(self.url, self._mails[0]["body_alternative"])

    def test_outside_images(self):
        """Should not replace them."""
        image_src = "http://localhostlocalhost:8069/image.png"
        with self.mock_mail_gateway():
            self.portal.with_context(mail_notify_force_send=True).message_post(
                body=f'<p>Checking <img src="{image_src}" alt="My Image"/></p>',
                subject="Test Email with External Image",
                partner_ids=self.partner.ids,
                attachments=[(self.attachment.name, self.attachment.datas)],
            )
        self.assertEqual(len(self._mails), 1)
        self.assertIn(
            "http://localhostlocalhost:8069", self._mails[0]["body_alternative"]
        )
