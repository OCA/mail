# © 2023 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import random

from odoo.tests import TransactionCase

_logger = logging.getLogger(__name__)


class TestActivity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.routing = cls.env["fetchmail.routing"].create(
            {
                "name": "Test Routing",
                "model_id": cls.env.ref("base.model_res_partner").id,
                "code": (
                    'ref = re.findall(r"<(REF\\d+)>", email["subject"])\n'
                    'result = [("ref", "in", ref)]'
                ),
            }
        )

    def test_misc(self):
        self.assertTrue(self.routing.help_text)
        self.assertTrue(self.routing._get_default_code())

    def test_logging(self):
        email_dict = {
            "email_from": "unknown@example.org",
            "to": "odoo@example.org",
            "recipients": "",
            "subject": "hello test <UNKNOWN>",
        }
        self.routing.code = "log('hello')"
        self.routing.find_thread(email_dict)

        self.routing.code = "log('hello %s', 'world')"
        self.routing.find_thread(email_dict)

        self.routing.code = "log('hello %s', 'world', level='debug')"
        self.routing.find_thread(email_dict)

        self.routing.code = "log()"
        with self.assertRaises(ValueError):
            self.routing.find_thread(email_dict)

    def test_find_thread(self):
        reference = f"REF{random.randint(1, 10000):06}"
        partner = self.env["res.partner"].create(
            {"name": "test", "email": "test@example.org", "ref": reference}
        )

        model, thread_id = self.env["fetchmail.routing"].find_thread(
            {
                "email_from": "unknown@example.org",
                "to": "odoo@example.org",
                "recipients": "",
                "subject": f"hello test <{reference}>",
            }
        )

        self.assertEqual((model, thread_id), (partner._name, partner.id))

        server = self.env["fetchmail.server"].create({"name": "abc"})
        self.routing.server_ids = server

        # Thread can still be found
        ctx_model = self.routing.with_context(default_fetchmail_server_id=server.id)
        model, thread_id = ctx_model.find_thread(
            {
                "email_from": "unknown@example.org",
                "to": "odoo@example.org",
                "recipients": "",
                "subject": f"hello test <{reference}>",
            }
        )
        self.assertEqual((model, thread_id), (partner._name, partner.id))

        # Non existing fetchmail server => no result
        ctx_model = self.routing.with_context(default_fetchmail_server_id=-42)
        model, thread_id = ctx_model.find_thread(
            {
                "email_from": "unknown@example.org",
                "to": "odoo@example.org",
                "recipients": "",
                "subject": f"hello test <{reference}>",
            }
        )
        self.assertEqual((model, thread_id), (None, None))

    def test_find_thread_duplicate(self):
        reference = f"REF{random.randint(1, 10000):06}"
        for _ in range(2):
            self.env["res.partner"].create(
                {"name": "test", "email": "test@example.org", "ref": reference}
            )

        with self.assertRaises(ValueError):
            self.env["fetchmail.routing"].find_thread(
                {
                    "email_from": "unknown@example.org",
                    "to": "odoo@example.org",
                    "recipients": "",
                    "subject": f"hello test <{reference}>",
                }
            )

    def test_find_thread_not_matching(self):
        reference = f"REF{random.randint(1, 10000):06}"
        self.assertEqual(
            self.env["fetchmail.routing"].find_thread(
                {
                    "email_from": "unknown@example.org",
                    "to": "odoo@example.org",
                    "recipients": "",
                    "subject": f"hello test <{reference}>",
                }
            ),
            (None, None),
        )

    def test_find_thread_known_thread(self):
        reference = f"REF{random.randint(1, 10000):06}"
        self.assertEqual(
            self.env["fetchmail.routing"].find_thread(
                {
                    "email_from": "unknown@example.org",
                    "to": "odoo@example.org",
                    "recipients": "",
                    "subject": f"hello test <{reference}>",
                },
                model="known",
                thread_id=42,
            ),
            ("known", 42),
        )
