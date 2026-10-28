# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import Form

from odoo.addons.base.tests.common import BaseCommon


class TestMailAttachExistingAttachmentAccount(BaseCommon):
    _test_user_groups = ("account.group_account_invoice",)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create({"name": "Test product"})
        cls.partner = cls.env["res.partner"].create(
            {"name": "Mr. Odoo", "email": "mr.odoo@example.org"}
        )
        cls.journal = cls.env["account.journal"].create(
            {"name": "Test sale journal", "code": "TSALE", "type": "sale"}
        )
        invoice_form = Form(
            cls.env["account.move"].with_context(default_move_type="out_invoice")
        )
        invoice_form.partner_id = cls.partner
        with invoice_form.invoice_line_ids.new() as line_form:
            line_form.product_id = cls.product
        cls.invoice = invoice_form.save()
        cls.invoice.action_post()
        cls.attachment = cls.env["ir.attachment"].create(
            {
                "name": "Existing attachment.pdf",
                "raw": b"%PDF-1.4 migration test",
                "res_model": cls.invoice._name,
                "res_id": cls.invoice.id,
            }
        )

    def test_account_invoice_send(self):
        compose = Form(
            self.env["account.move.send.wizard"].with_context(
                active_ids=self.invoice.ids,
                default_model=self.invoice._name,
                default_res_id=self.invoice.id,
                default_res_model=self.invoice._name,
            )
        )
        self.assertTrue(compose.can_attach_attachment)
        wizard = compose.save()
        self.assertEqual(wizard.display_object_attachment_ids, self.attachment)
        wizard.move_id = False
        self.assertFalse(wizard.display_object_attachment_ids)

    def test_account_invoice_send_object_attachment(self):
        compose = Form(
            self.env["account.move.send.wizard"].with_context(
                active_ids=self.invoice.ids,
                active_model=self.invoice._name,
            )
        )
        compose.object_attachment_ids = self.attachment
        wizard = compose.save()
        wizard.action_send_and_print()
        # Attachments are sent as copies linked to the posted message
        message = self.invoice.message_ids.filtered("attachment_ids")[:1]
        sent_attachment = message.attachment_ids.filtered(
            lambda att: att.name == self.attachment.name
        )
        self.assertEqual(sent_attachment.checksum, self.attachment.checksum)
