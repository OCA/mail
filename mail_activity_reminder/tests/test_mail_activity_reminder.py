# Copyright 2020 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import datetime

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import fields
from odoo.tests import common


class TestMailActivityReminder(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env = cls.env(
            context=dict(
                cls.env.context,
                tracking_disable=True,
                no_reset_password=True,
            )
        )
        cls.ResUsers = cls.env["res.users"]
        cls.Company = cls.env["res.company"]
        cls.MailActivityType = cls.env["mail.activity.type"]
        cls.MailActivity = cls.env["mail.activity"]
        cls.company_id = cls.env.company
        cls.now = datetime(2020, 4, 19, 15, 00)
        cls.today = cls.now.date()
        cls.model_res_partner = cls.env["ir.model"].search(
            [("model", "=", "res.partner")], limit=1
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})

    def test_none_reminders(self):
        activity_type = self.MailActivityType.create({"name": "Activity Type"})
        self.assertEqual(activity_type._get_reminder_offsets(), [])

    def test_empty_reminders(self):
        activity_type = self.MailActivityType.create(
            {"name": "Activity Type", "reminders": " -./"}
        )
        self.assertEqual(activity_type._get_reminder_offsets(), [])

    def test_delimiters(self):
        activity_type = self.MailActivityType.create(
            {"name": "Activity Type", "reminders": "0 1_2/3.4t5"}
        )
        self.assertEqual(activity_type._get_reminder_offsets(), [0, 1, 2, 3, 4, 5])

    def test_first_notice_is_reminder(self):
        activity_type = self.MailActivityType.create(
            {"name": "Activity Type", "reminders": "0"}
        )
        user = self.ResUsers.sudo().create(
            {
                "name": "User",
                "login": "user",
                "email": "user@example.com",
                "company_id": self.company_id.id,
            }
        )
        activity = self.MailActivity.create(
            {
                "summary": "Activity",
                "activity_type_id": activity_type.id,
                "res_model_id": self.model_res_partner.id,
                "res_id": self.partner.id,
                "date_deadline": self.today,
                "user_id": user.id,
            }
        )

        self.assertTrue(activity.last_reminder_local)

    def test_reminder_behaviour(self):
        activity_type = self.MailActivityType.create(
            {"name": "Activity Type", "reminders": "0/2"}
        )

        with freeze_time(self.now):
            activity = self.MailActivity.create(
                {
                    "summary": "Activity",
                    "activity_type_id": activity_type.id,
                    "res_model_id": self.model_res_partner.id,
                    "res_id": self.partner.id,
                    "date_deadline": self.today + relativedelta(days=5),
                    "user_id": self.env.user.id,
                }
            )

        with freeze_time(self.now):
            activities = self.MailActivity._get_activities_to_remind()
            self.assertFalse(activities)

        with freeze_time(self.now + relativedelta(days=2)):
            activities = self.MailActivity._get_activities_to_remind()
            self.assertFalse(activities)

        with freeze_time(self.now + relativedelta(days=3)):
            activities = self.MailActivity._get_activities_to_remind()
            self.assertEqual(activities, activity)
            activities.action_remind()

        with freeze_time(self.now + relativedelta(days=4)):
            activities = self.MailActivity._get_activities_to_remind()
            self.assertFalse(activities)

        with freeze_time(self.now + relativedelta(days=5)):
            activities = self.MailActivity._get_activities_to_remind()
            self.assertEqual(activities, activity)
            activities.action_remind()

        activity.unlink()
        with freeze_time(self.now + relativedelta(days=5)):
            activities = self.MailActivity._get_activities_to_remind()
            self.assertFalse(activities)

    def test_reminder_flow(self):
        activity_type = self.MailActivityType.create(
            {"name": "Activity Type", "reminders": "0/2"}
        )

        with freeze_time(self.now):
            activity = self.MailActivity.create(
                {
                    "summary": "Activity",
                    "activity_type_id": activity_type.id,
                    "res_model_id": self.model_res_partner.id,
                    "res_id": self.partner.id,
                    "date_deadline": self.today + relativedelta(days=5),
                    "user_id": self.env.user.id,
                }
            )

        with freeze_time(self.now):
            activities = self.MailActivity._process_reminders()
            self.assertFalse(activities)

        with freeze_time(self.now + relativedelta(days=2)):
            activities = self.MailActivity._process_reminders()
            self.assertFalse(activities)

        with freeze_time(self.now + relativedelta(days=3)):
            activities = self.MailActivity._process_reminders()
            self.assertEqual(activities, activity)

        with freeze_time(self.now + relativedelta(days=4)):
            activities = self.MailActivity._process_reminders()
            self.assertFalse(activities)

        with freeze_time(self.now + relativedelta(days=5)):
            activities = self.MailActivity._process_reminders()
            self.assertEqual(activities, activity)

    def test_repeated_reminder(self):
        activity_type = self.MailActivityType.create(
            {"name": "Activity Type", "reminders": "0"}
        )

        with freeze_time(self.now):
            activity = self.MailActivity.create(
                {
                    "summary": "Activity",
                    "activity_type_id": activity_type.id,
                    "res_model_id": self.model_res_partner.id,
                    "res_id": self.partner.id,
                    "date_deadline": self.today + relativedelta(days=1),
                    "user_id": self.env.user.id,
                }
            )

        with freeze_time(self.now + relativedelta(days=1)):
            activities = self.MailActivity._process_reminders()
            self.assertEqual(activities, activity)

            activities = self.MailActivity._process_reminders()
            self.assertFalse(activities)

    def test_overdue_reminder(self):
        activity_type = self.MailActivityType.create(
            {"name": "Activity Type", "reminders": "0"}
        )

        with freeze_time(self.now):
            self.MailActivity.create(
                {
                    "summary": "Activity",
                    "activity_type_id": activity_type.id,
                    "res_model_id": self.model_res_partner.id,
                    "res_id": self.partner.id,
                    "date_deadline": self.today + relativedelta(days=1),
                    "user_id": self.env.user.id,
                }
            )

        with freeze_time(self.now + relativedelta(days=2)):
            activities = self.MailActivity._get_activities_to_remind()
            self.assertFalse(activities)

    def _create_activity(self, activity_type, user, days, summary=None):
        return self.MailActivity.create(
            {
                "summary": summary or f"Activity {days:+d}",
                "activity_type_id": activity_type.id,
                "res_model_id": self.model_res_partner.id,
                "res_id": self.partner.id,
                "date_deadline": self.today + relativedelta(days=days),
                "user_id": user.id,
            }
        )

    def test_reminder_level(self):
        activity_type = self.MailActivityType.create(
            {"name": "Activity Type", "reminders": "0/2/5"}
        )
        no_reminder_type = self.MailActivityType.create({"name": "No Reminders"})
        with freeze_time(self.now):
            levels = {
                days: self._create_activity(
                    activity_type, self.env.user, days
                )._get_reminder_level(self.today)
                for days in (7, 6, 5, 3, 2, 1, 0, -1)
            }
            self.assertEqual(levels, {7: 0, 6: 0, 5: 1, 3: 1, 2: 2, 1: 2, 0: 3, -1: 3})
            activity = self._create_activity(no_reminder_type, self.env.user, 0)
            self.assertEqual(activity._get_reminder_level(self.today), 0)

    def test_reminder_report_sections(self):
        type_a = self.MailActivityType.create({"name": "Type A", "reminders": "0/2/5"})
        type_b = self.MailActivityType.create({"name": "Type B", "reminders": "1"})
        no_reminder_type = self.MailActivityType.create({"name": "No Reminders"})
        user = self.env.user
        with freeze_time(self.now):
            overdue_old = self._create_activity(type_a, user, -5)
            overdue_recent = self._create_activity(no_reminder_type, user, -1)
            level3 = self._create_activity(type_a, user, 0)
            level2_later = self._create_activity(type_a, user, 2)
            level2_sooner = self._create_activity(type_a, user, 1)
            level1_b = self._create_activity(type_b, user, 1)
            level1_a = self._create_activity(type_a, user, 4)
            not_yet = self._create_activity(type_a, user, 6)
            never = self._create_activity(no_reminder_type, user, 0)
            activities = (
                never
                | not_yet
                | level1_a
                | level1_b
                | level2_sooner
                | level2_later
                | level3
                | overdue_recent
                | overdue_old
            )
            sections = activities._get_reminder_report_sections(self.today)
        self.assertEqual(
            [(s["overdue"], s["level"]) for s in sections],
            [(True, 0), (False, 3), (False, 2), (False, 1)],
        )
        self.assertEqual(sections[0]["activities"], overdue_old | overdue_recent)
        self.assertEqual(sections[1]["activities"], level3)
        self.assertEqual(sections[2]["activities"], level2_sooner | level2_later)
        self.assertEqual(sections[3]["activities"], level1_b | level1_a)
        reported = self.MailActivity.browse()
        for section in sections:
            reported |= section["activities"]
        self.assertNotIn(not_yet, reported)
        self.assertNotIn(never, reported)

    def test_reminder_report_flow(self):
        activity_type = self.MailActivityType.create(
            {"name": "Activity Type", "reminders": "0/2"}
        )
        users = self.ResUsers.sudo().create(
            [
                {
                    "name": f"User {index}",
                    "login": f"reminder_report_user_{index}",
                    "email": f"reminder_report_user_{index}@example.com",
                    "company_id": self.company_id.id,
                }
                for index in range(3)
            ]
        )
        user_overdue, user_upcoming, user_quiet = users
        with freeze_time(self.now):
            overdue = self._create_activity(activity_type, user_overdue, -3)
            upcoming = self._create_activity(activity_type, user_upcoming, 1)
            self._create_activity(activity_type, user_quiet, 10)
            self._create_activity(activity_type, user_overdue, 10)
            # Done activities are archived and must not be reported
            done = self._create_activity(activity_type, user_quiet, -1)
            done.action_done()

            reported = self.MailActivity._process_reminder_report()
        self.assertEqual(reported, overdue | upcoming)

        messages = self.env["mail.message"].search(
            [("subject", "ilike", "Activity reminder report%")]
        )
        self.assertEqual(len(messages), 2)
        self.assertEqual(
            messages.partner_ids, user_overdue.partner_id | user_upcoming.partner_id
        )
        message_overdue = messages.filtered(
            lambda m: m.partner_ids == user_overdue.partner_id
        )
        self.assertIn("1 overdue, 0 upcoming", message_overdue.subject)
        body_overdue = " ".join(message_overdue.body.split())
        self.assertIn("Overdue by 3 day(s)", body_overdue)
        self.assertNotIn("Activity +10", body_overdue)
        message_upcoming = messages.filtered(
            lambda m: m.partner_ids == user_upcoming.partner_id
        )
        self.assertIn("0 overdue, 1 upcoming", message_upcoming.subject)
        body_upcoming = " ".join(message_upcoming.body.split())
        self.assertIn("Reminder 1 of 2", body_upcoming)
        # The report is not a reminder: the regular reminder is still due
        self.assertEqual(
            messages.mapped("email_layout_xmlid"),
            ["mail.mail_notification_light"] * 2,
        )
        with freeze_time(self.now + relativedelta(days=1)):
            self.assertIn(upcoming, self.MailActivity._get_activities_to_remind())

    def test_reminder_report_cron(self):
        cron = self.env.ref("mail_activity_reminder.mail_activity_reminder_report")
        self.assertEqual(cron.interval_type, "weeks")
        self.assertEqual(cron.interval_number, 1)
        self.assertEqual(cron.model_id.model, "mail.activity")

    def test_demo_data(self):
        single = self.env.ref(
            "mail_activity_reminder.mail_activity_type_single_reminder",
            raise_if_not_found=False,
        )
        if not single:
            self.skipTest("Demo data not installed")
        two = self.env.ref("mail_activity_reminder.mail_activity_type_two_reminders")
        self.assertEqual(single._get_reminder_offsets(), [2])
        self.assertEqual(two._get_reminder_offsets(), [0, 3])

        today = fields.Date.today()
        expected = {
            "mail_activity_single_overdue": (True, 1),
            "mail_activity_single_reminder_1": (False, 1),
            "mail_activity_single_planned": (False, 0),
            "mail_activity_two_overdue": (True, 2),
            "mail_activity_two_reminder_2": (False, 2),
            "mail_activity_two_reminder_1": (False, 1),
            "mail_activity_two_planned": (False, 0),
            "mail_activity_admin_two_reminder_1": (False, 1),
        }
        for xmlid, (overdue, level) in expected.items():
            activity = self.env.ref(f"mail_activity_reminder.{xmlid}")
            self.assertTrue(activity.active, xmlid)
            self.assertEqual(activity.date_deadline < today, overdue, xmlid)
            self.assertEqual(activity._get_reminder_level(today), level, xmlid)
        for xmlid in ("mail_activity_single_done", "mail_activity_two_done"):
            activity = self.env.ref(f"mail_activity_reminder.{xmlid}")
            self.assertFalse(activity.active, xmlid)
            self.assertTrue(activity.date_done, xmlid)

    def test_to_remind_filter(self):
        activity_type = self.MailActivityType.create(
            {"name": "Activity Type", "reminders": "0/2"}
        )
        no_reminder_type = self.MailActivityType.create({"name": "No Reminders"})
        user = self.env.user
        with freeze_time(self.now):
            overdue = self._create_activity(activity_type, user, -1)
            level2 = self._create_activity(activity_type, user, 0)
            level1 = self._create_activity(activity_type, user, 2)
            planned = self._create_activity(activity_type, user, 3)
            never = self._create_activity(no_reminder_type, user, 0)
            done = self._create_activity(activity_type, user, 1)
            done.action_done()
            activities = overdue | level2 | level1 | planned | never | done

            self.assertEqual(activities.mapped("reminder_level"), [2, 2, 1, 0, 0, 1])
            self.assertEqual(
                activities.mapped("to_remind"),
                [False, True, True, False, False, False],
            )
            domain = [("id", "in", activities.ids)]
            self.assertEqual(
                self.MailActivity.search(domain + [("to_remind", "=", True)]),
                level2 | level1,
            )
            self.assertEqual(
                self.MailActivity.search(domain + [("to_remind", "!=", True)]),
                overdue | planned | never,
            )
            self.assertEqual(
                self.MailActivity.search(domain + [("to_remind", "=", False)]),
                overdue | planned | never,
            )
            self.assertEqual(
                self.MailActivity.with_context(active_test=False).search(
                    domain + [("to_remind", "=", True)]
                ),
                level2 | level1,
            )

        with freeze_time(self.now + relativedelta(days=1)):
            # Non-stored computes are cached within the transaction
            activities.invalidate_recordset(["reminder_level", "to_remind"])
            self.assertFalse(level2.to_remind)
            self.assertEqual(
                self.MailActivity.search(domain + [("to_remind", "=", True)]),
                level1 | planned,
            )
