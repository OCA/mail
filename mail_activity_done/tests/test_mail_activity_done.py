# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import os

from odoo.modules.migration import load_script
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import BaseCommon


class TestMailActivityDone(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_existing_type(self):
        """The post init hook has enabled keeping done activities on all types"""
        self.assertTrue(self.env.ref("mail.mail_activity_data_email").keep_done)

    def test_new_type(self):
        """New activities will be configured to keep done activities by default"""
        activity_type = self.env["mail.activity.type"].create({"name": __name__})
        self.assertTrue(activity_type.keep_done)

    def test_migration(self):
        """The migration script will set keep done for all activity types.

        Also, because in Odoo 18 all archived activities are done, the migration
        will delete all archived activities that were not done before.
        """

        # Create two types with a different configuration
        activity_type1 = self.env["mail.activity.type"].create(
            {
                "name": __name__,
                "keep_done": False,
            }
        )
        self.assertFalse(activity_type1.keep_done)

        activity_type2 = self.env["mail.activity.type"].create({"name": __name__})

        # Create two activities
        act1 = self.env["mail.activity"].create(
            {
                "activity_type_id": activity_type2.id,
                "res_id": self.env.user.partner_id.id,
                "res_model": "res.partner",
                "res_model_id": self.env["ir.model"]._get("res.partner").id,
                "user_id": self.env.user.id,
                "date_deadline": "2024-01-01",
            }
        )
        act2 = act1.copy()
        act3 = act1.copy()

        # Set one activity done
        act1._action_done()
        self.assertEqual(act1.state, "done")

        # Set another one as archived
        act2.active = False
        # Archived activities are always done, which is not correct in this case
        self.assertEqual(act2.state, "done")
        self.env.flush_all()

        # Ressurect the obsolete 'done' column from 17.0 and set it for act1
        # to distinguish the previously done activity from the mere archived one.
        self.env.cr.execute(
            """
            alter table mail_activity add column done boolean;
            update mail_activity set done = true where id in %(act_ids)s;
            """,
            {"act_ids": (act1.id, act3.id)},
        )
        # The third activity is an inconsistent state as it is still active
        self.assertTrue(act3.active)

        # Run the migration script
        pyfile = os.path.join(
            "mail_activity_done",
            "migrations",
            "18.0.1.0.0",
            "post-migration.py",
        )
        name, ext = os.path.splitext(os.path.basename(pyfile))
        mod = load_script(pyfile, name)
        with mute_logger("odoo.addons.mail_activity_done.migrations"):
            mod.migrate(self.env.cr, "18.0.1.0.0")
        self.env.clear()

        # All types are now configured to keep done activities
        self.assertTrue(activity_type1.keep_done)
        self.assertTrue(activity_type2.keep_done)
        self.assertTrue(act1.exists())
        # Activities that were archived but not done are kept.
        self.assertTrue(act2.exists())
        # Activities that were unarchived and done are archived.
        self.assertFalse(act3.active)
