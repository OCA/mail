# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from lxml import etree

from odoo.tests.common import TransactionCase

from .common import read_eml


class TestMailGateway(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

    def _process(self, filename):
        record_id = self.env["mail.thread"].message_process(
            "res.partner", read_eml(filename, "rb")
        )
        return self.env["res.partner"].browse(record_id)

    def test_all_html_documents_are_kept(self):
        partner = self._process("multiple_html_documents.eml")
        body = partner.message_ids.filtered(lambda m: m.message_type == "email").body
        self.assertIn("First document", body)
        self.assertIn("Second document", body)

    def test_all_html_documents_can_be_turned_off(self):
        self.env.company.parse_all_html_documents_in_mail = False
        partner = self._process("multiple_html_documents.eml")
        body = partner.message_ids.filtered(lambda m: m.message_type == "email").body
        if etree.LIBXML_VERSION < (2, 10):
            # Older libxml2 already keeps every <html>
            self.assertIn("Second document", body)
        else:
            self.assertNotIn("Second document", body)
