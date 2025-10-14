from odoo.addons.mail.tests.test_mail_template import TestMailTemplate


class TestMailTemplateConditionalAttachment(TestMailTemplate):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.attachment_1 = cls.env["ir.attachment"].create(
            {
                "name": "Attachment 1",
                "type": "binary",
                "datas": "dGVzdA==",  # base64 for 'test'
                "mimetype": "text/plain",
            }
        )
        cls.attachment_2 = cls.env["ir.attachment"].create(
            {
                "name": "Attachment 2",
                "type": "binary",
                "datas": "dGVzdDI=",  # base64 for 'test2'
                "mimetype": "text/plain",
            }
        )
        cls.conditional_attachment_1 = cls.env[
            "mail.template.conditional.attachment"
        ].create(
            {
                "name": "Conditional Attachment 1",
                "mail_template_id": cls.mail_template.id,
                "attachment_ids": [(6, 0, [cls.attachment_1.id])],
            }
        )
        cls.conditional_attachment_2 = cls.env[
            "mail.template.conditional.attachment"
        ].create(
            {
                "name": "Conditional Attachment 2",
                "mail_template_id": cls.mail_template.id,
                "attachment_ids": [(6, 0, [cls.attachment_2.id])],
            }
        )

    def test_01_conditional_attachment_no_condition(self):
        """Test that attachments are added when no condition is set."""
        attachments = self.conditional_attachment_1.get_attachment_ids(
            self.user_employee.partner_id.id
        )
        self.assertIn(self.attachment_1, attachments)
        attachments = self.conditional_attachment_2.get_attachment_ids(
            self.user_employee.partner_id.id
        )
        self.assertIn(self.attachment_2, attachments)

    def test_02_conditional_attachment_with_condition(self):
        """Test that attachments are conditionally added based on the domain."""
        self.conditional_attachment_1.filter_domain = "[('is_company', '=', True)]"
        self.conditional_attachment_2.filter_domain = "[('is_company', '=', False)]"

        # The partner is not a company, so only attachment 2 should be added
        attachments = self.conditional_attachment_1.get_attachment_ids(
            self.user_employee.partner_id.id
        )
        self.assertNotIn(self.attachment_1, attachments)

        attachments = self.conditional_attachment_2.get_attachment_ids(
            self.user_employee.partner_id.id
        )
        self.assertIn(self.attachment_2, attachments)

        # Change the partner to a company and test again
        company_partner = self.env["res.partner"].create(
            {"name": "Company Partner", "is_company": True}
        )

        attachments = self.conditional_attachment_1.get_attachment_ids(
            company_partner.id
        )
        self.assertIn(self.attachment_1, attachments)

        attachments = self.conditional_attachment_2.get_attachment_ids(
            company_partner.id
        )
        self.assertNotIn(self.attachment_2, attachments)
