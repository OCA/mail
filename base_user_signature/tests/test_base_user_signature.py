from base64 import b64encode
from io import BytesIO

from PIL import Image

from odoo import Command
from odoo.exceptions import AccessError

from odoo.addons.base.tests.common import SavepointCaseWithUserDemo


class TestResUsersDigitalSignature(SavepointCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create(
            {
                "name": "Test User",
                "login": "test_user",
                "email": "test_user@example.com",
                "group_ids": [Command.set(cls.env.ref("base.group_user").ids)],
            }
        )
        cls.png = cls._generate_sample_png()
        cls.signature = b64encode(cls.png).decode("ascii")

    @classmethod
    def _generate_sample_png(cls):
        img = Image.new("RGB", (10, 10), color="red")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_01_user_signs_and_clears_own_signature(self):
        """An internal user draws a signature in their preferences, sees it
        saved, then clears it with the trash button."""
        me = self.user.with_user(self.user)
        me.write({"digital_signature": self.signature})
        me.invalidate_recordset()
        self.assertEqual(me.digital_signature.content, self.png)

        me.clear_digital_signature()
        me.invalidate_recordset()
        self.assertFalse(me.digital_signature)

    def test_02_user_cannot_sign_for_someone_else(self):
        """An internal user can read a colleague's signature but cannot
        replace it."""
        self.user_demo.digital_signature = self.signature
        colleague = self.user_demo.with_user(self.user)
        self.assertEqual(colleague.digital_signature.content, self.png)
        with self.assertRaises(AccessError):
            colleague.write({"digital_signature": False})
