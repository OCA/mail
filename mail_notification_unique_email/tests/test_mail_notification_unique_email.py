# Copyright 2026 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import tagged
from odoo.tools import email_normalize

from odoo.addons.mail.tests.common import MailCommon


@tagged("post_install", "-at_install")
class TestMailNotificationUniqueEmail(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create(
            {"name": "Customer", "email": "shop@example.com"}
        )
        cls.delivery = cls.env["res.partner"].create(
            {
                "name": "Final customer",
                "type": "delivery",
                "parent_id": cls.customer.id,
                "email": "Shop <SHOP@example.com>",
            }
        )
        cls.other = cls.env["res.partner"].create(
            {"name": "Other", "email": "other@example.com"}
        )
        cls.record = cls.env["res.partner"].create({"name": "Document"})
        cls.record.message_subscribe(
            partner_ids=(cls.customer | cls.delivery | cls.other).ids
        )

    def _post(self, partners=None):
        with self.mock_mail_gateway():
            message = self.record.message_post(
                body="Your order is on its way",
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                partner_ids=partners.ids if partners else [],
            )
        return message

    def _sent_to(self):
        return sorted(
            email_normalize(addr) for mail in self._mails for addr in mail["email_to"]
        )

    def test_followers_sharing_email_get_one_email(self):
        message = self._post()
        self.assertEqual(len(message.notification_ids), 2)
        self.assertIn(self.other, message.notification_ids.res_partner_id)
        self.assertEqual(self._sent_to(), ["other@example.com", "shop@example.com"])

    def test_addressed_partner_is_kept(self):
        message = self._post(self.delivery)
        self.assertEqual(
            message.notification_ids.res_partner_id, self.delivery | self.other
        )
        self.assertEqual(len(self._mails), 2)

    def test_internal_user_is_kept_before_customer(self):
        self.customer.email = self.user_admin.email
        self.user_admin.notification_type = "email"
        self.record.message_subscribe(partner_ids=self.partner_admin.ids)
        message = self._post(self.customer)
        self.assertEqual(
            message.notification_ids.res_partner_id,
            self.partner_admin | self.delivery | self.other,
        )

    def test_partners_without_email_are_not_merged(self):
        (self.customer | self.delivery).email = False
        message = self._post()
        self.assertEqual(
            message.notification_ids.res_partner_id,
            self.customer | self.delivery | self.other,
        )
