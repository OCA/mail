# Copyright 2015 ACSONE SA/NV
# Copyright 2024 360ERP (<https://www.360erp.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import Form

from odoo.addons.base.tests.common import BaseCommon


class TestMailComposer(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_01 = cls.env["res.partner"].create(
            {
                "name": "Partner 1",
                "email": "partner1@example.org",
                "parent_id": False,
            }
        )
        cls.attach1 = cls.env["ir.attachment"].create(
            {
                "name": "Attach1",
                "raw": b"migration test",
                "res_model": "res.partner",
                "res_id": cls.partner_01.id,
            }
        )
        cls.attach2 = cls.attach1.copy()
        cls.partner_02 = cls.partner_01.copy()
        cls.attach3 = cls.attach1.copy({"res_id": cls.partner_02.id})

    def test_01_send_email_attachment(self):
        """Test sending amail with attachment from Object Attachment of composer"""
        # Open email composer
        composer_form = Form(
            self.env["mail.compose.message"].with_context(
                default_composition_mode="comment",
                default_model=self.partner_01._name,
                default_res_ids=self.partner_01.ids,
            )
        )

        # Field can_attach_attachment is automatically set
        self.assertTrue(composer_form.can_attach_attachment)

        # By default, no attachments are present
        self.assertFalse(composer_form.partner_ids[:])
        self.assertEqual(len(composer_form.attachment_ids), 0)
        self.assertEqual(len(composer_form.object_attachment_ids), 0)

        # The record's Object Attachments are selectable
        display_records = composer_form.display_object_attachment_ids._records
        self.assertEqual(
            {record["id"] for record in display_records},
            set((self.attach1 + self.attach2).ids),
        )

        # Fill email composer with the Object Attachment
        composer_form.partner_ids = self.partner_01
        composer_form.object_attachment_ids = self.attach1
        mail = composer_form.save()

        # Send email: the attachment is sent
        values = mail._action_send_mail()
        result_message = values[1]
        self.assertEqual(result_message.attachment_ids, self.attach1)

    def test_02_prepare_mail_values(self):
        """Test method _prepare_mail_values()"""
        # Create email composer with 2 Object Attachments
        composer = (
            self.env["mail.compose.message"]
            .with_context(
                default_composition_mode="comment",
                default_model=self.partner_01._name,
                default_res_ids=self.partner_01.ids,
            )
            .create(
                {
                    "object_attachment_ids": (self.attach1 + self.attach2).ids,
                }
            )
        )

        # Two selectable Object Attachments are displayed
        display_records = composer.display_object_attachment_ids
        self.assertEqual(len(display_records), 2)
        self.assertIn(self.attach1, display_records)
        self.assertIn(self.attach2, display_records)

        # Invoking _prepare_mail_values(): both attachment_ids are set
        values = composer._prepare_mail_values(self.partner_01.ids)
        self.assertIn(self.attach1.id, values[self.partner_01.id]["attachment_ids"])
        self.assertIn(self.attach2.id, values[self.partner_01.id]["attachment_ids"])

    def test_03_display_object_attachment_no_model(self):
        """Test that display_object_attachment_ids is empty without model"""
        composer = self.env["mail.compose.message"].create({})
        self.assertFalse(composer.display_object_attachment_ids)

    def test_04_display_object_attachment_multi_composer(self):
        """Test that each composer computes its own selectable attachments"""
        composers = self.env["mail.compose.message"].create(
            [
                {
                    "composition_mode": "comment",
                    "model": partner._name,
                    "res_ids": partner.ids,
                }
                for partner in (self.partner_01, self.partner_02)
            ]
        )
        self.assertEqual(
            composers[0].display_object_attachment_ids, self.attach1 + self.attach2
        )
        self.assertEqual(composers[1].display_object_attachment_ids, self.attach3)

    def test_05_edit_message_cannot_attach_attachment(self):
        """Test that object attachments are not offered when editing a message"""
        message = self.partner_01.message_post(body="Test")
        composer_form = Form(
            self.env["mail.compose.message"].with_context(
                default_composition_mode="comment",
                default_model=self.partner_01._name,
                default_res_ids=self.partner_01.ids,
                default_message_id=message.id,
            )
        )
        self.assertFalse(composer_form.can_attach_attachment)
