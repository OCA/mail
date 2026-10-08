# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo.orm.model_classes import add_to_registry
from odoo.tests import Form, TransactionCase


class TestMailserverByModel(TransactionCase):
    at_install = False
    post_install = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, no_reset_password=True)
        )
        cls.setUpClassModels()
        cls.setUpClassMailserver()
        cls.setUpClassMail()

    @classmethod
    def setUpClassModels(cls):
        from .models import ModelWithMail

        add_to_registry(cls.registry, ModelWithMail)
        cls.addClassCleanup(cls.registry.__delitem__, ModelWithMail._name)
        cls.registry._setup_models__(cls.env.cr, [ModelWithMail._name])
        cls.registry.init_models(
            cls.env.cr, [ModelWithMail._name], {"models_to_check": True}
        )
        dest_partner = cls.env["res.partner"].create(
            {"name": "René Coty", "email": "rene.coty@gouv.fr"}
        )
        cls.record_with_mail = cls.env[ModelWithMail._name].create(
            {"partner_id": dest_partner.id}
        )
        cls.model_with_mail_model = cls.env["ir.model"].search(
            [("model", "=", ModelWithMail._name)]
        )

    @classmethod
    def setUpClassMailserver(cls):
        mailserver_model = cls.env["ir.mail_server"]
        cls.secondary_mailserver = mailserver_model.create(
            {
                "smtp_host": "localhost",
                "smtp_port": "25",
                "smtp_pass": "1 4m v3ry 53cur3",
                "smtp_authentication": "login",
                "smtp_encryption": "none",
                "name": "secondary",
                "smtp_user": "secondary@localhost",
                "sequence": 42,
            }
        )

    @classmethod
    def setUpClassMail(cls):
        cls.mail_template = cls.env["mail.template"].create(
            {
                "model_id": cls.model_with_mail_model.id,
                "name": "Model with Mail: Send by Mail",
                "subject": "Model with Mail: {{object.partner_id.name}}",
                "partner_to": "{{object.partner_id.id}}",
                "body_html": "Hello, this is a mail",
            }
        )

    def _create_notification_mail(self):
        """Create a queued notification email for the test model."""
        composer = Form(
            self.env["mail.compose.message"].with_context(
                default_model=self.record_with_mail._name,
                default_res_ids=self.record_with_mail.ids,
                default_use_template=True,
                default_template_id=self.mail_template.id,
                default_composition_mode="comment",
                mail_notify_force_send=False,
            )
        )
        _, messages = composer.save()._action_send_mail()
        self.assertEqual(len(messages), 1)
        mail = self.env["mail.mail"].search(
            [("mail_message_id", "=", messages.id)], limit=1
        )
        self.assertTrue(mail)
        return mail

    def test_00_default_outgoing_mail_settings(self):
        """Test notifications use the standard sender and server by default."""
        mail = self._create_notification_mail()
        self.assertFalse(mail.mail_server_id)
        self.assertTrue(mail.email_from)

    def test_01_outgoing_server_without_sender(self):
        """Test the model server overrides routing without changing the sender."""
        default_sender = self._create_notification_mail().email_from
        self.model_with_mail_model.outgoing_mailserver_id = self.secondary_mailserver
        mail = self._create_notification_mail()
        self.assertEqual(mail.mail_server_id, self.secondary_mailserver)
        self.assertEqual(mail.email_from, default_sender)

    def test_02_outgoing_sender_without_server(self):
        """Test the model sender overrides the address without forcing a server."""
        self.model_with_mail_model.outgoing_email = self.secondary_mailserver.smtp_user
        mail = self._create_notification_mail()
        self.assertFalse(mail.mail_server_id)
        self.assertEqual(mail.email_from, self.secondary_mailserver.smtp_user)

    def test_03_outgoing_server_and_sender(self):
        """Test notifications use both outgoing settings configured on the model."""
        self.model_with_mail_model.write(
            {
                "outgoing_mailserver_id": self.secondary_mailserver.id,
                "outgoing_email": self.secondary_mailserver.smtp_user,
            }
        )
        mail = self._create_notification_mail()
        self.assertEqual(mail.mail_server_id, self.secondary_mailserver)
        self.assertEqual(mail.email_from, self.secondary_mailserver.smtp_user)
