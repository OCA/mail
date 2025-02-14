# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.mail.tests.common import MailCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestMailCcBccInvoice(TestAccountMoveSendCommon, MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.partner = env.ref("base.res_partner_address_31")
        cls.partner_cc = env.ref("base.partner_demo")
        cls.partner_bcc = env.ref("base.res_partner_main2")

    def test_invoice_mail_cc_bcc(self):
        invoice = self.init_invoice(
            "out_invoice", partner=self.partner, amounts=[1000], post=True
        )
        wizard = self.create_send_and_print(
            invoice,
            sending_methods=["email", "manual"],
            mail_partner_ids=self.partner,
            partner_cc_ids=self.partner_cc,
            partner_bcc_ids=self.partner_bcc,
        )

        with self.mock_mail_gateway():
            wizard.action_send_and_print()
        self.assertEqual(len(self._mails), 3)

        message = self._get_mail_message(invoice)
        self.assertEqual(len(message.mail_ids), 1)

        # Only 3 partners (from default_cc/bcc of company) notified
        self.assertEqual(len(message.notified_partner_ids), 3)
        self.assertEqual(len(message.notification_ids), 3)
