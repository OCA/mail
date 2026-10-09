# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.addons.base.tests.common import BaseCommon


class TestMailActivityDone(BaseCommon):
    def test_existing_type(self):
        """The post init hook has enabled keeping done activities on all types"""
        self.assertTrue(self.env.ref("mail.mail_activity_data_email").keep_done)

    def test_new_type(self):
        """New activities will be configured to keep done activities by default"""
        activity_type = self.env["mail.activity.type"].create({"name": __name__})
        self.assertTrue(activity_type.keep_done)
