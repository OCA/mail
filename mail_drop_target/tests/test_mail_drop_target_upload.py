from odoo import http
from odoo.tests.common import HttpCase, tagged
from odoo.tools import file_open


@tagged("post_install", "-at_install")
class TestMailDropTargetUpload(HttpCase):
    def test_upload_email_on_channel(self):
        channel = self.env["discuss.channel"].create(
            {"name": "Drop target channel", "group_public_id": None}
        )
        channel.add_members(self.env.ref("base.partner_admin").ids)
        self.authenticate("admin", "admin")
        with file_open("mail_drop_target/tests/sample.eml", "rb") as file:
            response = self.url_open(
                "/mail/attachment/upload",
                {
                    "csrf_token": http.Request.csrf_token(self),
                    "thread_id": channel.id,
                    "thread_model": "discuss.channel",
                },
                files={"ufile": ("sample.eml", file.read())},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"email_upload": 1})
