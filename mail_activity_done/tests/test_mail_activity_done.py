# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import date

from odoo.tests.common import TransactionCase


class TestMailActivityDoneMethods(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = cls.env["res.users"].create(
            {
                "company_id": cls.env.ref("base.main_company").id,
                "name": "Test User",
                "login": "testuser",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        activity_type = cls.env["mail.activity.type"].search(
            [("name", "=", "Meeting")], limit=1
        )
        cls.act1 = cls.env["mail.activity"].create(
            {
                "activity_type_id": activity_type.id,
                "res_id": cls.env.ref("base.res_partner_1").id,
                "res_model": "res.partner",
                "res_model_id": cls.env["ir.model"]._get("res.partner").id,
                "user_id": cls.user.id,
                "date_deadline": date.today(),
            }
        )

    def test_mail_activity_done(self):
        self.act1._action_done()
        self.assertTrue(self.act1.exists())
        self.assertEqual(self.act1.state, "done")

    def test_get_activity_groups(self):
        act_count = self.user.with_user(self.user)._get_activity_groups()
        self.assertEqual(
            len(act_count), 1, "Number of activities should be equal to one"
        )
        self.assertEqual(act_count[0]["total_count"], 1)
        self.act1._action_done()
        self.act1.flush_recordset()
        act_count = self.user.with_user(self.user)._get_activity_groups()
        self.assertFalse(act_count)

    def test_read_progress_bar(self):
        partner = self.env["res.partner"].browse(self.act1.res_id)
        params = {
            "domain": [("id", "=", partner.id)],
            "group_by": "id",
            "progress_bar": {
                "field": "activity_state",
                "colors": {
                    "overdue": "danger",
                    "today": "warning",
                    "planned": "success",
                },
            },
        }
        # The activity is present in the progress bar
        self.assertEqual(
            partner.read_progress_bar(**params),
            {str(partner.id): {"overdue": 0, "today": 1, "planned": 0}},
        )
        # After marking the activity as done, it is removed from the progress bar
        self.act1._action_done()
        self.act1.flush_recordset()
        self.assertEqual(
            partner.read_progress_bar(**params),
            {str(partner.id): {"overdue": 0, "today": 0, "planned": 0}},
        )

    def test_activity_state_search(self):
        today_activities = self.env["res.partner"].search(
            [("activity_state", "=", "today")]
        )
        self.assertEqual(len(today_activities), 1)
        overdue_activities = self.env["res.partner"].search(
            [("activity_state", "=", "overdue")]
        )
        self.assertFalse(overdue_activities)

        # After the activity is marked as done, the activity state is unmarked
        self.act1._action_done()
        today_activities = self.env["res.partner"].search(
            [("activity_state", "=", "today")]
        )
        self.assertFalse(today_activities)
