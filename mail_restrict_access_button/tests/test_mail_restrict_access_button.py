# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMailRestrictAccessButton(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.record = cls.env.ref("base.main_partner")

    def _base_groups(self):
        original_groups = self.record._notify_get_recipients_groups(
            self.env["mail.message"],
            False,
        )
        for group in original_groups:
            group[2]["active"] = True
        main_customer_group = [
            "main_customer",
            lambda r: r["id"] == 1,
            {"has_button_access": True, "active": True},
        ]
        return [main_customer_group] + original_groups

    def _pdata(self, rtype, is_follower=False):
        return [
            {
                "id": 1,
                "uid": False if rtype == "customer" else 1,
                "type": rtype,
                "is_follower": is_follower,
                "active": True,
            }
        ]

    def test_unregistered_customer_has_no_button(self):
        # Unregistered customer does not have button access
        with patch.object(
            type(self.record),
            "_notify_get_recipients_groups",
            return_value=self._base_groups(),
        ):
            group_data = self.record._notify_get_recipients_classify(
                False, self._pdata("customer"), "Document"
            )
        self.assertEqual(len(group_data), 1)
        name = group_data[0].get("notification_group_name")
        has_button_access = group_data[0].get("has_button_access")
        self.assertEqual(name, "customer")
        self.assertFalse(has_button_access)

    def test_registered_portal_user_keeps_button(self):
        # Portal recipient has button access even in main_customer group
        with patch.object(
            type(self.record),
            "_notify_get_recipients_groups",
            return_value=self._base_groups(),
        ):
            group_data = self.record._notify_get_recipients_classify(
                False, self._pdata("portal"), "Document"
            )
        self.assertEqual(len(group_data), 1)
        name = group_data[0].get("notification_group_name")
        has_button_access = group_data[0].get("has_button_access")
        self.assertEqual(name, "main_customer")
        self.assertTrue(has_button_access)

    def test_internal_user_keeps_button(self):
        # Internal user recipient has button access even in main_customer group
        with patch.object(
            type(self.record),
            "_notify_get_recipients_groups",
            return_value=self._base_groups(),
        ):
            group_data = self.record._notify_get_recipients_classify(
                False, self._pdata("user"), "Document"
            )
        self.assertEqual(len(group_data), 1)
        name = group_data[0].get("notification_group_name")
        has_button_access = group_data[0].get("has_button_access")
        self.assertEqual(name, "main_customer")
        self.assertTrue(has_button_access)

    def test_unregistered_filter_applies_to_any_button_group(self):
        # Unregistered follower lands in follower because it has no button
        base_groups = self._base_groups()
        with patch.object(
            type(self.record), "_notify_get_recipients_groups", return_value=base_groups
        ):
            group_data = self.record._notify_get_recipients_classify(
                False, self._pdata("customer", is_follower=True), "Document"
            )
            self.assertEqual(len(group_data), 1)
            name = group_data[0].get("notification_group_name")
            has_button_access = group_data[0].get("has_button_access")
            self.assertEqual(name, "follower")
            self.assertFalse(has_button_access)
        # Registered portal user matches main_customer and keeps their button
        base_groups = self._base_groups()
        with patch.object(
            type(self.record), "_notify_get_recipients_groups", return_value=base_groups
        ):
            group_data = self.record._notify_get_recipients_classify(
                False, self._pdata("portal", is_follower=True), "Document"
            )
            self.assertEqual(len(group_data), 1)
            name = group_data[0].get("notification_group_name")
            has_button_access = group_data[0].get("has_button_access")
            self.assertEqual(name, "main_customer")
            self.assertTrue(has_button_access)
        # Modify 'follower' to have a button
        # Unregistered user must now be blocked and drop to customer
        base_groups = self._base_groups()
        next(g for g in base_groups if g[0] == "follower")[2]["has_button_access"] = (
            True
        )
        with patch.object(
            type(self.record), "_notify_get_recipients_groups", return_value=base_groups
        ):
            group_data = self.record._notify_get_recipients_classify(
                False, self._pdata("customer", is_follower=True), "Document"
            )
            self.assertEqual(len(group_data), 1)
            name = group_data[0].get("notification_group_name")
            has_button_access = group_data[0].get("has_button_access")
            self.assertEqual(name, "customer")
            self.assertFalse(has_button_access)
        # Modifying follower doesn't block the registered portal user
        base_groups = self._base_groups()
        next(g for g in base_groups if g[0] == "follower")[2]["has_button_access"] = (
            True
        )
        with patch.object(
            type(self.record), "_notify_get_recipients_groups", return_value=base_groups
        ):
            group_data = self.record._notify_get_recipients_classify(
                False, self._pdata("portal", is_follower=True), "Document"
            )
            self.assertEqual(len(group_data), 1)
            name = group_data[0].get("notification_group_name")
            has_button_access = group_data[0].get("has_button_access")
            self.assertEqual(name, "main_customer")
            self.assertTrue(has_button_access)

    def test_unregistered_classified_when_every_group_has_a_button(self):
        # If every group is turned into a button group, the unregistered
        # customer still matches the buttonless fallback group
        base_groups = self._base_groups()
        for group in base_groups:
            group[2]["has_button_access"] = True
        with patch.object(
            type(self.record), "_notify_get_recipients_groups", return_value=base_groups
        ):
            group_data = self.record._notify_get_recipients_classify(
                False, self._pdata("customer"), "Document"
            )
            self.assertEqual(len(group_data), 1)
            name = group_data[0].get("notification_group_name")
            has_button_access = group_data[0].get("has_button_access")
            self.assertEqual(name, "unregistered_external")
            self.assertFalse(has_button_access)
