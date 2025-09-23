import email
import uuid

from odoo.tests.common import TransactionCase

MESSAGE_ID = f"<{uuid.uuid4()}@example.org>"
MAIL = f"""
Content-Type: multipart/mixed; boundary="------------6S5GIA0a7bmD9z4YzFLV1oIL"
Message-ID: {MESSAGE_ID}
Date: Sat, 18 Feb 2023 15:01:13 +0100
MIME-Version: 1.0
Content-Language: en-US
To: test@localhost, second <second@localhost>
Cc: cc@localhost
Bcc: bcc@localhost
From: test <test@example.org>
Subject: hello

This is a multi-part message in MIME format.
--------------6S5GIA0a7bmD9z4YzFLV1oIL
Content-Type: text/plain; charset=UTF-8; format=flowed
Content-Transfer-Encoding: 7bit

hello world<br/>hello world 2

--------------6S5GIA0a7bmD9z4YzFLV1oIL
Content-Type: text/plain; charset=UTF-8; name="att abc.txt"
Content-Disposition: attachment; filename="att abc.txt"
Content-Transfer-Encoding: base64

aGVsbG8gd29ybGQ=

--------------6S5GIA0a7bmD9z4YzFLV1oIL--
""".strip()


class TestUnassignedMails(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.thread = cls.env.user.partner_id
        cls.model = cls.env["mail.unassigned"]
        cls.model.search([]).unlink()

        message = email.message_from_bytes(MAIL.encode(), policy=email.policy.SMTP)
        cls.msg_dict = cls.thread.message_parse(message)

    def test_assignment(self):
        self.env.company.use_unassigned_mails = False
        self.model.process_unassigned(MAIL, self.msg_dict)
        self.assertEqual(self.model.search_count([]), 0)

        self.env.company.use_unassigned_mails = True
        self.model.process_unassigned(MAIL, self.msg_dict)
        self.assertEqual(self.model.search_count([]), 1)

        rec = self.model.search([("message_id", "=", MESSAGE_ID)])
        self.assertTrue(rec)

        self.env["fetchmail.server"]._fetch_mails()
        self.assertTrue(rec.exists())

        rec.thread_id = f"{self.thread._name},{self.thread.id}"
        self.env["fetchmail.server"]._fetch_mails()
        self.assertFalse(rec.exists())

    def test_assignment_create(self):
        self.env.company.use_unassigned_mails = True
        self.model.process_unassigned(MAIL, self.msg_dict)
        self.assertEqual(self.model.search_count([]), 1)

        rec = self.model.search([("message_id", "=", MESSAGE_ID)])
        self.assertTrue(rec)

        self.env["fetchmail.server"]._fetch_mails()
        self.assertTrue(rec.exists())

        rec.model = self.thread._name
        before = self.thread.search_count([])
        self.env["fetchmail.server"]._fetch_mails()
        self.assertFalse(rec.exists())
        self.assertEqual(before + 1, self.thread.search_count([]))

    def test_find_thread(self):
        self.env.company.use_unassigned_mails = True
        self.model.process_unassigned(MAIL, self.msg_dict)
        self.model.process_unassigned(MAIL, self.msg_dict)
        self.assertEqual(self.model.search_count([]), 1)

        rec = self.model.search([("message_id", "=", MESSAGE_ID)])
        self.assertTrue(rec)
        self.assertEqual(
            self.model.find_thread(self.msg_dict, "unknown", 0),
            ("unknown", 0),
        )

        rec.thread_id = f"{self.thread._name},{self.thread.id}"
        self.assertEqual(
            self.model.find_thread(self.msg_dict, "unknown", 0),
            (self.thread._name, self.thread.id),
        )

        self.assertEqual(
            self.model.find_thread(self.msg_dict, "unknown", 42),
            ("unknown", 42),
        )

        self.env.company.use_unassigned_mails = False
        self.assertEqual(
            self.model.find_thread(self.msg_dict, "unknown", 0),
            ("unknown", 0),
        )

    def test_miscellaneous(self):
        # Check that there is no exception
        self.model._gc_remove_old_unassigned_mails()

    def test_wizard(self):
        self.env.company.use_unassigned_mails = True
        self.model.process_unassigned(MAIL, self.msg_dict)
        rec = self.model.search([("message_id", "=", MESSAGE_ID)])
        self.assertTrue(rec)

        context = rec.action_assign()["context"]

        wiz = (
            self.env["mail.assign.wizard"]
            .with_context(**context)
            .create({"operation": "existing"})
        )
        self.assertEqual(wiz.mail_ids, rec)

        wiz.action_assign()
        self.assertFalse(rec.thread_id)

        before = len(self.thread.message_ids)
        wiz.thread_id = f"{self.thread._name},{self.thread.id}"
        wiz.action_assign()
        self.assertEqual(len(self.thread.message_ids), before + 1)

    def test_wizard_same_thread(self):
        self.env.company.use_unassigned_mails = True
        self.model.process_unassigned(MAIL, self.msg_dict)
        recs = self.model.search([("message_id", "=", MESSAGE_ID)])
        self.assertEqual(len(recs), 1)

        message_id = f"<{uuid.uuid4()}@example.org>"
        recs |= recs.copy(
            {
                "message_id": message_id,
                "message": recs.message.replace(MESSAGE_ID, message_id),
            }
        )

        wiz = self.env["mail.assign.wizard"].create(
            {
                "mail_ids": [(6, 0, recs.ids)],
                "thread_per_mail": True,
                "model": self.thread._name,
                "operation": "new",
            }
        )

        before = self.thread.search([])
        wiz.action_assign()
        thread = self.thread.search([]) - before
        self.assertFalse(recs.exists())
        self.assertTrue(thread)
        self.assertEqual(
            set(thread.message_ids.mapped("message_id")), {MESSAGE_ID, message_id}
        )
