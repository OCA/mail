# Copyright - 2015-2026 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# pylint: disable=method-required-super
from datetime import datetime
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests.common import TransactionCase
from odoo.tools.mail import email_normalize

from ..match_algorithm import email_domain, email_exact
from .common import get_message_body

TEST_EMAIL = "reynaert@dutchsagas.nl"
TEST_SUBJECT = "Test subject"
MAIL_MESSAGE = {"subject": TEST_SUBJECT, "to": "demo@yourcompany.example.com"}


class MockConnection:
    _msg_store = {}

    def select(self, path=None):
        if path in ("INBOX", "customers", "archived_messages"):
            return ("OK",)
        return ("NO",)

    def create(self, path):
        """Mock creating a folder."""
        return ("OK",)

    def store(self, message_uid, msg_item, value):
        """Mock store command.

        Actually simplified. We only store te latest flag set (or unset), in the
        real IMAP folder there can be multiple flags on a message.
        """
        if message_uid not in self._msg_store:
            self._msg_store[message_uid] = {}
        msg_key = msg_item[1:]  # Remove + or -
        if msg_item == "-FLAGS":  # This is to remove flags
            self._msg_store[message_uid][msg_key] = ""
        else:
            self._msg_store[message_uid][msg_key] = value
        return "OK"

    def copy(self, message_uid, folder_path):
        """Mock copy command."""
        return "OK"

    def fetch(self, message_uid, parts):
        """Return RFC822 formatted message.

        By passing special values in message_uid, we can manipulate
        the body returned.
        """
        if message_uid == "deleted_uid":
            return ("BAD", "")
        email = (
            "the_smart_red_one@reynaerde.waesland"
            if message_uid == "test no match"
            else TEST_EMAIL
        )
        return ("OK", get_message_body(email, TEST_SUBJECT))

    def search(self, charset, criteria):
        """Return some message uid's."""
        if criteria == "test_invalid":
            return ("BAD", [])
        return ("OK", ["123 456"])

    def close(self):
        pass

    def logout(self):
        pass

    def expunge(self):
        """Mock an IMAP4.expunge action"""
        return ("OK", None)

    def uid(self, command, *args):
        """Return from the appropiate mocked method."""
        method = getattr(self, command)
        return method(*args)


class TestMatchAlgorithms(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.PartnerCategory = cls.env["res.partner.category"]
        cls.partner_category = cls.PartnerCategory.create({"name": "Test Partners"})
        cls.Partner = cls.env["res.partner"]
        cls.test_partner = cls.Partner.with_context(tracking_disable=True).create(
            {
                "name": "Reynaert de Vos",
                "email": TEST_EMAIL,
                "is_company": False,
                "category_id": [Command.clear()],
            }
        )
        cls.FetchmailServer = cls.env["fetchmail.server"]
        cls.FetchmailServerFolder = cls.env["fetchmail.server.folder"]
        cls.server = cls.FetchmailServer.create(
            {
                "name": "Test Fetchmail Server",
                "server": "imap.example.com",
                "server_type": "imap",
                "folders_only": True,  # Not going to test default fetchmail
                "active": True,
                "state": "done",
            }
        )
        cls.folder = cls.FetchmailServerFolder.create(
            {
                "server_id": cls.server.id,
                "sequence": 5,
                "path": "INBOX",
                "model_id": cls.env.ref("base.model_res_partner").id,
                "model_field": "email",
                "match_algorithm": "email_exact",
                # The intention is to link email to sender partner object.
                "mail_field": "from",
            }
        )
        partner_ir_model = cls.env["ir.model"].search(
            [
                ("model", "=", cls.Partner._name),
            ],
            limit=1,
        )
        cls.server_action = cls.env["ir.actions.server"].create(
            {
                "name": "Action Set Active Partner",
                "state": "object_write",
                "update_path": "category_id",
                "evaluation_type": "value",
                "value": str(cls.partner_category.id),
                "model_id": partner_ir_model.id,
            }
        )

    def test_server(self):
        """Test the server model."""
        self.server.write({"server_type": "pop"})
        self.assertEqual(self.server.state, "draft")
        self._reactivate_server()
        self.assertEqual(self.server.state, "done")
        with patch.object(
            self.server.__class__, "_connect__", return_value=MockConnection()
        ):
            self.server.fetch_mail()
        self.server.onchange_server_type()
        self.assertEqual(self.server.state, "draft")

    def _reactivate_server(self):
        """Set type to imap and state to "done"."""
        self.server.write(
            {
                "server_type": "imap",
                "active": True,
                "state": "done",
            }
        )

    def test_email_exact(self):
        """A message to ronald@acme.com should be linked to partner with that email."""
        MAIL_MESSAGE["from"] = TEST_EMAIL
        self._test_search_matches(email_exact.EmailExact)
        self._test_apply_matching(email_exact.EmailExact)

    def test_email_exact_duplicate(self):
        """If two partners have same email, return 1st or none, depending on config."""
        connection = MockConnection()
        folder = self.folder
        folder.match_algorithm = "email_exact"
        folder.match_first = False
        extra_partner = self.Partner.with_context(tracking_disable=True).create(
            {
                "name": "The Young Fox",
                "email": TEST_EMAIL,
                "is_company": False,
            }
        )
        MAIL_MESSAGE["from"] = TEST_EMAIL
        matcher = email_exact.EmailExact()
        matches = matcher.search_matches(folder, MAIL_MESSAGE)
        self.assertEqual(len(matches), 2)
        thread_id = folder.apply_matching(connection, "does not really matter")
        self.assertFalse(thread_id)
        folder.match_first = True
        thread_id = folder.apply_matching(connection, "does not really matter")
        self.assertIn(thread_id, [self.test_partner.id, extra_partner.id])

    def test_email_domain(self):
        """Test with email in same domain, but different mailbox."""
        ALTERNATE_EMAIL = TEST_EMAIL.replace("reynaert@", "mariken@")
        MAIL_MESSAGE["from"] = ALTERNATE_EMAIL
        self.folder.match_algorithm = "email_domain"
        self.folder.match_first = True
        self._test_search_matches(email_domain.EmailDomain)
        self._test_apply_matching(email_domain.EmailDomain)

    def _test_search_matches(self, match_algorithm):
        matcher = match_algorithm()
        matches = matcher.search_matches(self.folder, MAIL_MESSAGE)
        # matches should be a record set with length 1.
        self.assertEqual(matches.email, self.test_partner.email)
        self.assertEqual(matches, self.test_partner)

    def _test_apply_matching(self, match_algorithm):
        connection = MockConnection()
        thread_id = self.folder.apply_matching(connection, "1")
        self.assertEqual(thread_id, self.test_partner.id)
        self.assertEqual(self.test_partner.message_ids[-1].subject, TEST_SUBJECT)

    def test_apply_matching_exact(self):
        folder = self.folder
        folder.match_algorithm = "email_exact"
        connection = MockConnection()
        message_uid = "<485a8041-d560-a981-5afc-d31c1f136748@acme.com>"
        folder.apply_matching(connection, message_uid)

    def test_apply_matching_exact_no_match(self):
        folder = self.folder
        folder.match_algorithm = "email_exact"
        connection = MockConnection()
        message_uid = "test no match"
        folder.apply_matching(connection, message_uid)

    def test_apply_matching_odoo_standard(self):
        folder = self.folder
        folder.match_algorithm = "odoo_standard"
        connection = MockConnection()
        message_uid = "test no match"
        thread_id = folder.apply_matching(connection, message_uid)
        self.assertTrue(thread_id)  # Odoo standard either updates of creates record.
        partner = self.Partner.browse(thread_id)
        self.assertTrue(partner)
        self.assertEqual(
            email_normalize(partner.email), "the_smart_red_one@reynaerde.waesland"
        )

    def test_retrieve_imap_folder_domain(self):
        folder = self.folder
        folder.match_algorithm = "email_domain"
        connection = MockConnection()
        folder.retrieve_imap_folder(connection)

    def test_archive_messages(self):
        folder = self.folder
        folder.archive_path = "archived_messages"
        connection = MockConnection()
        folder.check_imap_archive_folder(connection)
        # Apply matching should succeed with no error.
        folder.match_algorithm = "email_exact"
        message_uid = "<485a8041-d560-a981-5afc-d31c1f136748@acme.com>"
        folder.apply_matching(connection, message_uid)
        # Should fail on not existing folder that is not autocreated.
        with self.assertRaises(UserError):
            folder.archive_path = "will_not_be_created"
            folder.check_imap_archive_folder(connection)
        # Should not fail if no archive path.
        folder.archive_path = False
        folder.check_imap_archive_folder(connection)
        # Archiving should simply not fail.
        folder._archive_msg(connection, "does not matter")

    def test_non_action(self):
        connection = MockConnection()
        self.folder.action_id = False
        self.folder.apply_matching(connection, "1")
        self.assertFalse(self.test_partner.category_id)

    def test_get_criteria(self):
        self.folder.write({"fetch_unseen_only": False, "fetch_last_day_only": False})
        criteria = self.folder.get_criteria()
        self.assertEqual(criteria, "UNDELETED")
        self.folder.write({"fetch_unseen_only": True, "fetch_last_day_only": False})
        criteria = self.folder.get_criteria()
        self.assertEqual(criteria, "UNSEEN UNDELETED")
        self.folder.write({"fetch_last_day_only": True})
        criteria = self.folder.get_criteria()
        criteria_words = criteria.split()
        criteria_words[0] = "SINCE"
        since_date = datetime.strptime(criteria_words[1], "%d-%b-%Y").date()
        yesterday = fields.Date.subtract(fields.Date.context_today(self.folder), days=1)
        self.assertEqual(since_date, yesterday)

    def test_action(self):
        connection = MockConnection()
        self.folder.action_id = self.server_action
        self.folder.apply_matching(connection, "1")
        self.assertEqual(self.partner_category, self.test_partner.category_id)

    def test_button_confirm_folder(self):
        """Test the button_confirm_folder method."""
        folder = self.folder
        with patch.object(
            self.server.__class__, "_connect__", return_value=MockConnection()
        ):
            # Inactive folders are not set to done
            folder.active = False
            folder.button_confirm_folder()
            self.assertEqual(folder.state, "draft")
            # Active folders are set to done
            folder.active = True
            folder.button_confirm_folder()
            self.assertEqual(folder.state, "done")
            # Should fail on unknown folder.
            with self.assertRaises(ValidationError):
                folder.path = "invalid_folder"
                folder.button_confirm_folder()

    def test_fetchmail(self):
        """Test the overall process."""
        folder = self.folder
        with patch.object(
            self.server.__class__, "_connect__", return_value=MockConnection()
        ):
            # Should not result in error if not active or in draft.
            folder.active = False
            folder.button_confirm_folder()
            self.assertEqual(folder.state, "draft")
            folder.fetch_mail()
            # Should also not result in error if active.
            folder.active = True
            folder.button_confirm_folder()
            self.assertEqual(folder.state, "done")
            folder.fetch_mail()

    def test_fetch_msg_exception(self):
        """There can be an exception, for example if message no longer exists."""
        folder = self.folder
        connection = MockConnection()
        with self.assertRaises(UserError):
            folder.fetch_msg(connection, "deleted_uid")

    def test_get_message_uids(self):
        """Test failure on invalid criteria."""
        folder = self.folder
        connection = MockConnection()
        criteria = folder.get_criteria()
        message_uids = folder.get_message_uids(connection, criteria)
        self.assertEqual(message_uids, ["123 456"])
        folder.path = "invalid_folder"
        with self.assertRaises(UserError):
            folder.get_message_uids(connection, criteria)
        folder.path = "INBOX"  # Restore valid folder path.
        criteria = "test_invalid"
        with self.assertRaises(UserError):
            folder.get_message_uids(connection, criteria)

    def test_update_msg(self):
        """Message update depends on folder configuration."""
        folder = self.folder
        connection = MockConnection()
        folder.seen = "matching"
        folder.update_msg(connection, "123", matched=True)
        self._check_flags(connection, "123", "\\Seen")
        folder.seen = "on_fetch"  # back to default
        folder.delete_matching = True
        folder.update_msg(connection, "456", matched=True)
        self._check_flags(connection, "456", "\\DELETED")
        folder.delete_matching = False  # back to default
        self.flag_nonmatching = True
        folder.update_msg(connection, "789", matched=True, flagged=True)
        self._check_flags(connection, "789", "")

    def _check_flags(self, connection, uid, expected_flags):
        """Check whether expected value stored."""
        self.assertIn(uid, connection._msg_store)
        self.assertIn("FLAGS", connection._msg_store[uid])
        self.assertEqual(connection._msg_store[uid]["FLAGS"], expected_flags)

    def test_get_partner_from_object(self):
        """When object refers to partner, return that partner."""
        folder = self.folder
        company_partner = folder._get_partner_from_object(self.env.company)
        self.assertEqual(self.env.company.partner_id, company_partner)
        # Object with no partner_id should return empty recordset.
        server_partner = folder._get_partner_from_object(self.server)
        self.assertEqual(server_partner._name, "res.partner")
        self.assertEqual(len(server_partner), 0)

    def test_button_attach_mail_manually(self):
        """The button should return the an action dictionary."""
        folder = self.folder
        action_dict = folder.button_attach_mail_manually()
        Wizard = self.env[action_dict["res_model"]]
        self.assertEqual(Wizard._name, "fetchmail.attach.mail.manually")

    def test_set_draft(self):
        """Test the set_draft method."""
        folder = self.folder
        res = folder.set_draft()
        self.assertEqual(res, True)
        self.assertEqual(folder.state, "draft")
