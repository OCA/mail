# Copyright 2024 - Today: GRAP (http://www.grap.coop)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command
from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestMailDiscussSecurity(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_discuss = cls.env.ref("mail_discuss_security.group_discuss")
        cls.menu_discuss = cls.env.ref("mail.menu_root_discuss")
        cls.user_without_group = cls.env["res.users"].create(
            {
                "name": "Test user without discuss group",
                "login": "test_mail_discuss_without_group",
                "groups_id": [Command.set(cls.group_user.ids)],
            }
        )
        cls.user_with_group = cls.env["res.users"].create(
            {
                "name": "Test user with discuss group",
                "login": "test_mail_discuss_with_group",
                "groups_id": [Command.set(cls.group_user.ids + cls.group_discuss.ids)],
            }
        )

    def test_group_definition(self):
        self.assertEqual(self.group_discuss.name, "See Discuss Menu")
        self.assertNotIn(self.group_user, self.group_discuss.implied_ids)
        self.assertNotIn(self.group_user, self.group_discuss.trans_implied_ids)

    def test_menu_restricted_to_group(self):
        self.assertIn(self.group_discuss, self.menu_discuss.groups_id)
        self.assertNotIn(self.group_user, self.menu_discuss.groups_id)

    def test_menu_visibility(self):
        visible_ids = (
            self.env["ir.ui.menu"]
            .with_user(self.user_without_group)
            ._visible_menu_ids()
        )
        self.assertNotIn(self.menu_discuss.id, visible_ids)
        visible_ids = (
            self.env["ir.ui.menu"].with_user(self.user_with_group)._visible_menu_ids()
        )
        self.assertIn(self.menu_discuss.id, visible_ids)

    def test_group_has_no_rights(self):
        self.assertFalse(self.group_discuss.model_access)
        self.assertFalse(self.group_discuss.rule_groups)
