# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import Form, tagged

from odoo.addons.mail.tests.common import MailCommon


@tagged("-at_install", "post_install")
class TestMailSend(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env.ref("base.res_partner_address_31")
        cls.partner_cc = cls.env.ref("base.partner_demo")
        cls.partner_cc2 = cls.env.ref("base.partner_demo_portal")
        cls.partner_bcc = cls.env.ref("base.res_partner_main1")
        cls.mail_template = cls._create_template(
            "res.partner",
            template_values={
                "auto_delete": False,
                "email_to": cls.partner.email,
                "email_cc": cls.partner_cc.email,
                "email_bcc": cls.partner_bcc.email,
            },
        )

    def open_mail_composer_form(self):
        ctx = {
            "default_partner_ids": self.partner.ids,
            "default_model": self.partner._name,
            "default_res_ids": self.partner.ids,
            "mail_notify_force_send": True,
        }
        form = Form(self.env["mail.compose.message"].with_context(**ctx))
        form.body = "<p>Hello</p>"
        return form

    def test_email_to_cc_bcc_via_composer(self):
        """Sending via composer populates email_to, cc, bcc on mail.message."""
        form = self.open_mail_composer_form()
        composer = form.save()
        composer.partner_cc_ids = self.partner_cc | self.partner_cc2
        composer.partner_bcc_ids = self.partner_bcc
        with self.mock_mail_gateway():
            composer._action_send_mail()
        message = self.partner.message_ids[0]
        self.assertEqual(message.email_to, self.partner.email)  # add this
        self.assertIn(self.partner_cc.email, message.email_cc)
        self.assertIn(self.partner_cc2.email, message.email_cc)
        self.assertEqual(message.email_bcc, self.partner_bcc.email)

    def test_email_to_cc_via_template(self):
        """Sending via template populates email_to and email_cc on mail.message."""
        Mail = self.env["mail.mail"]
        mail_id = self.mail_template.send_mail(self.partner.id, force_send=True)
        mail = Mail.browse(mail_id)
        message = mail.mail_message_id
        self.assertEqual(message.email_to, self.partner.email)
        self.assertEqual(message.email_cc, self.partner_cc.email)
