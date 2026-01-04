# Copyright 2023 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.base.tests.common import BaseCommon


class TestActivityUnlink(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.unlink_subtype = cls.env.ref(
            "mail_activity_unlink_log.mt_activities_unlink"
        )

    def test_done(self):
        self.assertFalse(
            self.partner.message_ids.filtered(
                lambda r: r.subtype_id == self.unlink_subtype
            )
        )
        self.activity = self.partner.activity_schedule(
            act_type_xmlid="mail.mail_activity_data_todo"
        )
        self.assertTrue(self.partner.activity_ids)
        self.activity.action_done()
        self.assertFalse(self.partner.activity_ids)
        self.assertFalse(
            self.partner.message_ids.filtered(
                lambda r: r.subtype_id == self.unlink_subtype
            )
        )

    def test_unlink(self):
        self.assertFalse(
            self.partner.message_ids.filtered(
                lambda r: r.subtype_id == self.unlink_subtype
            )
        )
        self.activity = self.partner.activity_schedule(
            act_type_xmlid="mail.mail_activity_data_todo"
        )
        self.assertTrue(self.partner.activity_ids)
        self.activity.unlink()
        self.assertFalse(self.partner.activity_ids)
        self.assertTrue(
            self.partner.message_ids.filtered(
                lambda r: r.subtype_id == self.unlink_subtype
            )
        )

    def test_mixin_unlink(self):
        # No unlink messages initially
        self.assertFalse(
            self.partner.message_ids.filtered(
                lambda r: r.subtype_id == self.unlink_subtype
            )
        )

        # Create an activity on the partner
        self.partner.activity_schedule(act_type_xmlid="mail.mail_activity_data_todo")
        self.assertTrue(self.partner.activity_ids)

        # Unlink the partner → triggers mail.activity.mixin.unlink
        self.partner.unlink()

        # No unlink message should be posted because of the context flag
        messages = self.env["mail.message"].search(
            [("subtype_id", "=", self.unlink_subtype.id)]
        )
        self.assertFalse(messages)
