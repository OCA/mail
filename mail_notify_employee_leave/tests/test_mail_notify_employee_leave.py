# Copyright 2026 ForgeFlow S.L.
#   (http://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, time

from odoo import fields
from odoo.tests.common import TransactionCase


class TestNotifyEmployeeLeave(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = cls.env["res.users"].create(
            {
                "name": "Test User",
                "login": "test_user",
                "email": "test@example.com",
                "notification_type": "inbox",
            }
        )

        cls.absent_user = cls.env["res.users"].create(
            {
                "name": "Absent User",
                "login": "absent_user",
                "email": "absent@example.com",
                "notification_type": "inbox",
            }
        )

        cls.partner = cls.absent_user.partner_id

        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Absent Employee",
                "user_id": cls.absent_user.id,
            }
        )

        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Test Leave",
                "leave_validation_type": "no_validation",
                "requires_allocation": "no",
            }
        )

        cls.record = cls.env["res.partner"].create({"name": "Test Record"})

    @classmethod
    def _create_validated_leave(cls):
        today = fields.Date.today()
        leave = (
            cls.env["hr.leave"]
            .with_context(skip_absence_notification=True)
            .create(
                {
                    "holiday_status_id": cls.leave_type.id,
                    "employee_id": cls.employee.id,
                    "date_from": datetime.combine(today, time(0, 0, 0)),
                    "date_to": datetime.combine(today, time(23, 59, 59)),
                }
            )
        )
        leave.sudo().action_validate()
        return leave

    def test_no_notify_when_user_not_absent(self):
        self.record.with_user(self.user).message_post(
            body="Test message", partner_ids=[self.partner.id]
        )

        self.assertNotIn(self.user, self.employee.absence_notified_user_ids)

    def test_notify_when_user_absent(self):
        self._create_validated_leave()

        self.record.with_user(self.user).message_post(
            body="Test message", partner_ids=[self.partner.id]
        )

        self.assertIn(self.user, self.employee.absence_notified_user_ids)
        self.assertEqual(self.employee.absence_notified_date, fields.Date.today())

    def test_only_one_notification_per_day(self):
        self._create_validated_leave()

        self.record.with_user(self.user).message_post(
            body="Test message 1", partner_ids=[self.partner.id]
        )

        self.record.with_user(self.user).message_post(
            body="Test message 2", partner_ids=[self.partner.id]
        )

        notified_users = self.employee.absence_notified_user_ids
        self.assertEqual(len(notified_users), 1)
        self.assertIn(self.user, notified_users)
        self.assertEqual(self.employee.absence_notified_date, fields.Date.today())
