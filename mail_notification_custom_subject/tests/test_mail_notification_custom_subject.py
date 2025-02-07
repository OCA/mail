# Copyright 2020 Tecnativa - João Marques
# Copyright 2022-2025 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests import new_test_user
from odoo.tests.common import users
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import BaseCommon


class TestMailNotificationCustomSubject(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_1, cls.partner_2 = cls.env["res.partner"].create(
            [
                {"name": "Test partner 1", "email": "partner1@example.com"},
                {"name": "Test partner 2", "email": "partner2@example.com"},
            ]
        )
        cls.admin = new_test_user(cls.env, "boss", "base.group_system")
        new_test_user(cls.env, "worker_custom_subject")
        cls.subject_model = cls.env["mail.message.custom.subject"].with_user(cls.admin)

    @users("worker_custom_subject")
    def test_email_subject_template_overrides(self):
        self.subject_model.create(
            {
                "name": "Test template 1",
                "model_id": self.env.ref("base.model_res_partner").id,
                "subtype_ids": [(6, 0, [self.env.ref("mail.mt_comment").id])],
                "subject_template": "{{object.name or 'n/a'}} and something more",
            }
        )
        # Send message in partner
        mail_message_1 = self.partner_1.message_post(
            body="Test", subtype_xmlid="mail.mt_comment"
        )
        # Get message and check subject
        self.assertEqual(mail_message_1.subject, "Test partner 1 and something more")

        # Send message in partner 2
        mail_message_2 = self.partner_2.message_post(
            body="Test", subtype_xmlid="mail.mt_comment"
        )
        # Get message and check subject
        self.assertEqual(mail_message_2.subject, "Test partner 2 and something more")

        # Explicit subject should not also overwritten
        mail_message_3 = self.partner_2.message_post(
            body="Test", subtype_xmlid="mail.mt_comment", subject="Test"
        )
        # Get message and check subject
        self.assertEqual(mail_message_3.subject, "Test")

    @users("worker_custom_subject")
    def test_email_subject_template_inside_replace(self):
        self.subject_model.create(
            {
                "name": "Test template",
                "model_id": self.env.ref("base.model_res_partner").id,
                "subtype_ids": [(6, 0, [self.env.ref("mail.mt_comment").id])],
                "subject_to_replace": "{{object.company_id.name}}",
                "subject_template": "CLN",
                "position": "inside_replace",
            }
        )
        self.partner_1.company_id = self.env.company
        self.partner_1.company_id.name = "COMPANY_LONG_NAME"
        mail_message_1 = self.partner_1.message_post(
            subject="COMPANY_LONG_NAME: Custom",
            body="Test",
            subtype_xmlid="mail.mt_comment",
        )
        self.assertEqual(mail_message_1.subject, "CLN: Custom")

    @users("worker_custom_subject")
    def test_email_subject_template_normal(self):
        self.subject_model.create(
            {
                "name": "Test template 1",
                "model_id": self.env.ref("base.model_res_partner").id,
                "subtype_ids": [(6, 0, [self.env.ref("mail.mt_comment").id])],
                "subject_template": "{{object.name or 'n/a'}} and something more",
            }
        )
        # Send note in partner
        mail_message_1 = self.partner_1.message_post(
            body="Test", subtype_xmlid="mail.mt_note", subject="Test"
        )
        # Get message and check subject. Subject Template should not apply
        self.assertEqual(mail_message_1.subject, "Test")

    @users("worker_custom_subject")
    def test_email_subject_template_multi(self):
        self.subject_model.create(
            {
                "name": "Test template 1",
                "model_id": self.env.ref("base.model_res_partner").id,
                "subtype_ids": [(6, 0, [self.env.ref("mail.mt_comment").id])],
                "subject_template": "{{object.name or 'n/a'}} and something more",
            }
        )
        self.subject_model.create(
            {
                "name": "Test template 2",
                "model_id": self.env.ref("base.model_res_partner").id,
                "subtype_ids": [(6, 0, [self.env.ref("mail.mt_comment").id])],
                "subject_template": "{{object.name or 'n/a'}} and "
                "something different",
            }
        )
        # Send message in partner
        mail_message_1 = self.partner_1.message_post(
            body="Test", subtype_xmlid="mail.mt_comment"
        )
        # Get message and check subject
        self.assertEqual(
            mail_message_1.subject, "Test partner 1 and something different"
        )
        self.subject_model.create(
            {
                "name": "Test template 3",
                "model_id": self.env.ref("base.model_res_partner").id,
                "subtype_ids": [(6, 0, [self.env.ref("mail.mt_comment").id])],
                "subject_template": "{{' and yet something else'}}",
                "position": "append_after",
            }
        )
        # Send message in partner
        mail_message_2 = self.partner_1.message_post(
            body="Test", subtype_xmlid="mail.mt_comment"
        )
        # Get message and check subject
        self.assertEqual(
            mail_message_2.subject,
            "Test partner 1 and something different and yet something else",
        )
        self.subject_model.create(
            {
                "name": "Test template 4",
                "model_id": self.env.ref("base.model_res_partner").id,
                "subtype_ids": [(6, 0, [self.env.ref("mail.mt_comment").id])],
                "subject_template": "{{'Re: '}}",
                "position": "append_before",
            }
        )
        # Send message in partner
        mail_message_3 = self.partner_1.message_post(
            body="Test", subtype_xmlid="mail.mt_comment"
        )
        # Get message and check subject
        self.assertEqual(
            mail_message_3.subject,
            "Re: Test partner 1 and something different and yet something else",
        )

    @users("worker_custom_subject")
    def test_email_subject_template_w_original(self):
        self.subject_model.create(
            {
                "name": "Test template 1",
                "model_id": self.env.ref("base.model_res_partner").id,
                "subtype_ids": [(6, 0, [self.env.ref("mail.mt_comment").id])],
                "subject_template": "{{' and something more'}}",
                "position": "append_after",
            }
        )
        # Send message in partner
        mail_message_1 = self.partner_1.message_post(
            body="Test",
            subtype_xmlid="mail.mt_comment",
            subject="Test",
        )
        # Get message and check subject
        self.assertEqual(mail_message_1.subject, "Test and something more")

    @users("worker_custom_subject")
    @mute_logger(
        "odoo.addons.mail.models.mail_render_mixin",
        "odoo.addons.mail_notification_custom_subject.models.mail_thread",
    )
    def test_bad_template_does_not_break(self):
        """Create template with error (obaject) to test error."""
        self.subject_model.create(
            {
                "name": "Test bad template 1",
                "model_id": self.env.ref("base.model_res_partner").id,
                "subtype_ids": [(6, 0, [self.env.ref("mail.mt_comment").id])],
                "subject_template": "{{obaject.number_a}} and something",
                "position": "append_after",
            }
        )
        # Send message in partner
        mail_message_1 = self.partner_1.message_post(
            body="Test",
            subtype_xmlid="mail.mt_comment",
            subject="Test",
        )
        # Get message and check subject
        # No exception should be raised but subject should remain as original.
        self.assertEqual(mail_message_1.subject, "Test")

    @users("worker_custom_subject")
    def test_no_template_default_result(self):
        # Send message in partner
        mail_message_1 = self.partner_1.message_post(
            body="Test", subtype_xmlid="mail.mt_comment", subject="Test partner 1"
        )
        # Get message and check subject
        # No exception should be raised but subject should remain as original.
        self.assertEqual(mail_message_1.subject, "Test partner 1")
