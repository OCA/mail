# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import logging
import os
import re
from email import message_from_string
from unittest.mock import patch

from odoo import tools
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.base.tests.common import MockSmtplibCase

_logger = logging.getLogger(__name__)


class TestIrMailServer(TransactionCase, MockSmtplibCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.email_from = "derp@example.com"
        cls.email_from_another = "another@example.com"
        cls.IrMailServer = cls.env["ir.mail_server"]
        cls.parameter_model = cls.env["ir.config_parameter"]
        cls._delete_mail_servers()
        cls.IrMailServer.create(
            {
                "name": "localhost",
                "smtp_host": "localhost",
                "smtp_from": cls.email_from,
            }
        )
        message_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "test.msg"
        )
        with open(message_file) as fh:
            cls.message = message_from_string(fh.read())

    @classmethod
    def _delete_mail_servers(cls):
        """Delete all available mail servers"""
        all_mail_servers = cls.IrMailServer.search([])
        if all_mail_servers:
            all_mail_servers.unlink()

    def _init_mail_server_domain_whilelist_based(self):
        self._delete_mail_servers()
        self.assertFalse(self.IrMailServer.search([]))
        self.mail_server_domainone = self.IrMailServer.create(
            {
                "name": "sandbox domainone",
                "smtp_host": "localhost",
                "smtp_from": "notifications@domainone.com",
                "domain_whitelist": "domainone.com",
            }
        )
        self.mail_server_domaintwo = self.IrMailServer.create(
            {
                "name": "sandbox domaintwo",
                "smtp_host": "localhost",
                "smtp_from": "hola@domaintwo.com",
                "domain_whitelist": "domaintwo.com",
            }
        )
        self.mail_server_domainthree = self.IrMailServer.create(
            {
                "name": "sandbox domainthree",
                "smtp_host": "localhost",
                "smtp_from": "notifications@domainthree.com",
                "domain_whitelist": "domainthree.com,domainmulti.com",
            }
        )

    def _send_mail(self, message, mail_server_id=None):
        """
        This helper calls the real send_email method.
        It's intended to be used inside a `mock_smtplib_connection`
        context, which will prevent any real emails from being sent.
        The message object is modified in-place and returned for inspection.
        """
        self.IrMailServer.send_email(message, mail_server_id=mail_server_id)
        return message

    def test_send_email_injects_from_no_canonical(self):
        """It should inject the FROM header correctly when no canonical name."""
        self.message.replace_header("From", "test@example.com")
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(message["From"], self.email_from)

    def test_send_email_injects_from_with_canonical(self):
        """It should inject the FROM header correctly with a canonical name.

        Note that there is an extra `<` in the canonical name to test for
        proper handling in the split.
        """
        user = "Test < User"
        self.message.replace_header("From", f"{user} <test@example.com>")
        bounce_parameter = self.parameter_model.search(
            [("key", "=", "mail.bounce.alias")]
        )
        if bounce_parameter:
            # Remove mail.bounce.alias to test Return-Path
            bounce_parameter.unlink()
        # Also check passing mail_server_id
        mail_server_id = (
            self.IrMailServer.sudo().search([], order="sequence", limit=1)[0].id
        )
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message, mail_server_id=mail_server_id)
        self.assertEqual(message["From"], f'"{user}" <{self.email_from}>')
        self.assertEqual(message["Return-Path"], f'"{user}" <{self.email_from}>')

    def test_01_from_outgoing_server_domainone(self):
        self._init_mail_server_domain_whilelist_based()
        domain = "domainone.com"
        email_from = f"Mitchell Admin <admin@{domain}>"
        expected_mail_server = self.mail_server_domainone

        self.message.replace_header("From", email_from)
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(message["From"], email_from)

        used_mail_server = self.IrMailServer._get_mail_sever(domain)
        used_mail_server = self.IrMailServer.browse(used_mail_server)
        self.assertEqual(
            used_mail_server,
            expected_mail_server,
            (
                f"It using {used_mail_server.name}"
                f" but we expect to use {expected_mail_server.name}"
            ),
        )

    def test_02_from_outgoing_server_domaintwo(self):
        self._init_mail_server_domain_whilelist_based()
        domain = "domaintwo.com"
        email_from = f"Mitchell Admin <admin@{domain}>"
        expected_mail_server = self.mail_server_domaintwo

        self.message.replace_header("From", email_from)
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(message["From"], email_from)

        used_mail_server = self.IrMailServer._get_mail_sever(domain)
        used_mail_server = self.IrMailServer.browse(used_mail_server)
        self.assertEqual(
            used_mail_server,
            expected_mail_server,
            (
                f"It using {used_mail_server.name}"
                f" but we expect to use {expected_mail_server.name}"
            ),
        )

    def test_03_from_outgoing_server_another(self):
        self._init_mail_server_domain_whilelist_based()
        domain = "example.com"
        email_from = f"Mitchell Admin <admin@{domain}>"
        expected_mail_server = self.mail_server_domainone

        self.message.replace_header("From", email_from)
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(
            message["From"], f'"Mitchell Admin" <{expected_mail_server.smtp_from}>'
        )

        used_mail_server = self.IrMailServer._get_mail_sever(domain)
        used_mail_server = self.IrMailServer.browse(used_mail_server)
        self.assertEqual(
            used_mail_server,
            expected_mail_server,
            (
                f"It using {used_mail_server.name}"
                f" but we expect to use {expected_mail_server.name}"
            ),
        )

    @patch.dict(tools.config.options, {"smtp_from": "admin@example.com"})
    @patch.dict(tools.config.options, {"smtp_domain_whitelist": "example.com"})
    def test_04_from_outgoing_server_none_use_config(self):
        self._init_mail_server_domain_whilelist_based()
        domain = "example.com"
        email_from = f"Mitchell Admin <admin@{domain}>"

        self._delete_mail_servers()
        self.assertFalse(self.IrMailServer.search([]))
        # Find config values
        config_smtp_from = tools.config.get("smtp_from")
        config_smtp_domain_whitelist = tools.config.get("smtp_domain_whitelist")
        self.assertTrue(config_smtp_from)
        self.assertTrue(config_smtp_domain_whitelist)

        self.message.replace_header("From", email_from)
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(message["From"], f"Mitchell Admin <{config_smtp_from}>")

        used_mail_server = self.IrMailServer._get_mail_sever("example.com")
        used_mail_server = self.IrMailServer.browse(used_mail_server)
        self.assertFalse(
            used_mail_server, f"using this mail server {used_mail_server.name}"
        )

    @patch.dict(tools.config.options, {"smtp_from": "admin@example.com"})
    @patch.dict(tools.config.options, {"smtp_domain_whitelist": "example.com"})
    def test_05_from_outgoing_server_none_same_domain(self):
        self._init_mail_server_domain_whilelist_based()

        # Find config values
        config_smtp_from = tools.config.get("smtp_from")
        config_smtp_domain_whitelist = domain = tools.config.get(
            "smtp_domain_whitelist"
        )
        self.assertTrue(config_smtp_from)
        self.assertTrue(config_smtp_domain_whitelist)

        email_from = f"Mitchell Admin <admin@{domain}>"

        self._delete_mail_servers()
        self.assertFalse(self.IrMailServer.search([]))
        self.message.replace_header("From", email_from)
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(message["From"], email_from)

        used_mail_server = self.IrMailServer._get_mail_sever(domain)
        used_mail_server = self.IrMailServer.browse(used_mail_server)
        self.assertFalse(used_mail_server)

    def test_06_from_outgoing_server_no_name_from(self):
        self._init_mail_server_domain_whilelist_based()
        domain = "example.com"
        email_from = f"test@{domain}"
        expected_mail_server = self.mail_server_domainone

        self.message.replace_header("From", email_from)
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(message["From"], expected_mail_server.smtp_from)

        used_mail_server = self.IrMailServer._get_mail_sever(domain)
        used_mail_server = self.IrMailServer.browse(used_mail_server)
        self.assertEqual(
            used_mail_server,
            expected_mail_server,
            (
                f"It using {used_mail_server.name}"
                f" but we expect to use {expected_mail_server.name}"
            ),
        )

    def test_07_from_outgoing_server_multidomain_1(self):
        self._init_mail_server_domain_whilelist_based()
        domain = "domainthree.com"
        email_from = f"Mitchell Admin <admin@{domain}>"
        expected_mail_server = self.mail_server_domainthree

        self.message.replace_header("From", email_from)
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(message["From"], email_from)

        used_mail_server = self.IrMailServer._get_mail_sever(domain)
        used_mail_server = self.IrMailServer.browse(used_mail_server)
        self.assertEqual(
            used_mail_server,
            expected_mail_server,
            (
                f"It using {used_mail_server.name}"
                f" but we expect to use {expected_mail_server.name}"
            ),
        )

    def test_08_from_outgoing_server_multidomain_3(self):
        self._init_mail_server_domain_whilelist_based()
        domain = "domainmulti.com"
        email_from = f"test@{domain}"
        expected_mail_server = self.mail_server_domainthree

        self.message.replace_header("From", email_from)
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(message["From"], email_from)

        used_mail_server = self.IrMailServer._get_mail_sever(domain)
        used_mail_server = self.IrMailServer.browse(used_mail_server)
        self.assertEqual(
            used_mail_server,
            expected_mail_server,
            (
                f"It using {used_mail_server.name}"
                f" but we expect to use {expected_mail_server.name}"
            ),
        )

    def test_09_not_valid_domain_whitelist(self):
        self._init_mail_server_domain_whilelist_based()
        mail_server = self.mail_server_domainone
        mail_server.domain_whitelist = "example.com"
        error_msg = (
            "%s is not a valid domain. Please define a list of valid"
            " domains separated by comma"
        )

        with self.assertRaisesRegex(ValidationError, error_msg % "asdasd"):
            mail_server.domain_whitelist = "asdasd"

        with self.assertRaisesRegex(ValidationError, error_msg % "asdasd"):
            mail_server.domain_whitelist = "example.com, asdasd"

        with self.assertRaisesRegex(ValidationError, error_msg % "invalid"):
            mail_server.domain_whitelist = "example.com; invalid"

        with self.assertRaisesRegex(ValidationError, error_msg % ";"):
            mail_server.domain_whitelist = ";"

        with self.assertRaisesRegex(ValidationError, error_msg % "."):
            mail_server.domain_whitelist = "hola.com,."

    def test_10_not_valid_smtp_from(self):
        self._init_mail_server_domain_whilelist_based()
        mail_server = self.mail_server_domainone
        error_msg = "Not a valid Email From"

        with self.assertRaisesRegex(ValidationError, error_msg):
            mail_server.smtp_from = "asdasd"

        with self.assertRaisesRegex(ValidationError, error_msg):
            mail_server.smtp_from = "example.com"

        with self.assertRaisesRegex(ValidationError, error_msg):
            mail_server.smtp_from = "."

        mail_server.smtp_from = "notifications@test.com"

    def test_11_from_outgoing_server_another_special_char_comma(self):
        self._init_mail_server_domain_whilelist_based()
        domain = "example.com"
        email_from = f'"Muster, Jörg" <admin@{domain}>'
        expected_mail_server = self.mail_server_domainone

        self.message.replace_header("From", email_from)
        # A mail server is configured for the email
        with self.mock_smtplib_connection():
            message = self._send_mail(self.message)
        self.assertEqual(
            message["From"], f'"Muster, Jörg" <{expected_mail_server.smtp_from}>'
        )

        used_mail_server = self.IrMailServer._get_mail_sever(domain)
        used_mail_server = self.IrMailServer.browse(used_mail_server)
        self.assertEqual(
            used_mail_server,
            expected_mail_server,
            (
                f"It using {used_mail_server.name}"
                f" but we expect to use {expected_mail_server.name}"
            ),
        )

    def test_12_domain_whitelist_whitespace_handling(self):
        """Test whitespace around commas in domain_whitelist."""
        self._init_mail_server_domain_whilelist_based()
        mail_server = self.mail_server_domainone

        # This should pass validation due to the .strip() in the list comprehension
        mail_server.domain_whitelist = "  domainone.com ,  other.com  "

        # Verify it was stored
        self.assertTrue(mail_server.domain_whitelist)

        # Test that the error message formatting uses %s correctly
        # We pass an invalid domain with spaces to trigger the error
        invalid_input = "invalid space"
        # The error message in the code uses % (domain)
        expected_error = (
            f"{invalid_input} is not a valid domain. Please define a list of"
            " valid domains separated by comma"
        )

        with self.assertRaisesRegex(ValidationError, re.escape(expected_error)):
            mail_server.domain_whitelist = invalid_input

    def test_13_restore_display_name_after_super_strip(self):
        """Test that the display name is restored if super() strips it."""
        self._init_mail_server_domain_whilelist_based()
        domain = "domainone.com"
        name = "Mitchell Admin"
        email = f"admin@{domain}"
        # Use tools.formataddr to ensure we match
        # the quoting behavior of the implementation
        full_from = tools.formataddr((name, email))

        # Ensure we are using the whitelisted server
        mail_server = self.mail_server_domainone
        self.assertEqual(mail_server.domain_whitelist, domain)

        self.message.replace_header("From", full_from)

        # Define a side effect to simulate Odoo core stripping the name
        # This ensures the modification happens *during* the call, not before
        def side_effect(message, smtp_session):
            # Simulate Odoo core returning just the email address (name stripped)
            # We modify the message object in place as Odoo does
            message.replace_header("From", email)
            return email, ["to@example.com"], message

        # Patch the method on the class so the super() call inside the module hits this
        # send_email will capture the full context first, then call super(),
        # which hits our side_effect, which strips the name.
        # Then the module logic should restore it.
        with (
            patch(
                "odoo.addons.base.models.ir_mail_server.IrMail_Server._prepare_email_message__",
                side_effect=side_effect,
            ),
            self.mock_smtplib_connection(),
        ):
            result_message = self._send_mail(self.message)

        self.assertEqual(result_message["From"], full_from)

    def _is_lookup_cached(self, email_domain):
        """Return True if _get_mail_sever has a cached value for this domain"""
        missing = object()
        cache = self.IrMailServer._get_mail_sever.__cache__
        value = cache.get_value(self.IrMailServer, email_domain, cache_default=missing)
        return value is not missing

    def test_14_unrelated_write_keeps_cache(self):
        """Writing a field not used by the lookup keeps the cache."""
        self._init_mail_server_domain_whilelist_based()
        self.IrMailServer._get_mail_sever("domainone.com")
        self.assertTrue(self._is_lookup_cached("domainone.com"))

        self.mail_server_domainone.write(
            {"name": "renamed server", "smtp_host": "smtp.example.com"}
        )
        self.assertTrue(self._is_lookup_cached("domainone.com"))

        # smtp_from is used when sending, but not by the server lookup
        self.mail_server_domainone.smtp_from = "other@domainone.com"
        self.assertTrue(self._is_lookup_cached("domainone.com"))

    def test_15_domain_whitelist_write_refreshes_lookup(self):
        """Changing domain_whitelist clears the cache and updates the lookup."""
        self._init_mail_server_domain_whilelist_based()
        lookup = self.IrMailServer._get_mail_sever
        self.assertEqual(lookup("domainfour.com"), self.mail_server_domainone.id)

        self.mail_server_domaintwo.domain_whitelist = "domaintwo.com,domainfour.com"
        self.assertFalse(self._is_lookup_cached("domainfour.com"))
        self.assertEqual(lookup("domainfour.com"), self.mail_server_domaintwo.id)

    def test_16_sequence_write_refreshes_lookup(self):
        """Changing sequence clears the cache and updates the default server."""
        self._init_mail_server_domain_whilelist_based()
        lookup = self.IrMailServer._get_mail_sever
        servers = (
            self.mail_server_domainone
            | self.mail_server_domaintwo
            | self.mail_server_domainthree
        )
        servers.sequence = 10
        self.mail_server_domainthree.sequence = 1
        self.assertEqual(lookup("example.com"), self.mail_server_domainthree.id)

        self.mail_server_domaintwo.sequence = 0
        self.assertFalse(self._is_lookup_cached("example.com"))
        self.assertEqual(lookup("example.com"), self.mail_server_domaintwo.id)

    def test_17_archive_refreshes_lookup(self):
        """Archiving a server clears the cache, so it is no longer used."""
        self._init_mail_server_domain_whilelist_based()
        lookup = self.IrMailServer._get_mail_sever
        self.assertEqual(lookup("domaintwo.com"), self.mail_server_domaintwo.id)

        self.mail_server_domaintwo.active = False
        self.assertFalse(self._is_lookup_cached("domaintwo.com"))
        self.assertNotEqual(lookup("domaintwo.com"), self.mail_server_domaintwo.id)

        self.mail_server_domaintwo.active = True
        self.assertFalse(self._is_lookup_cached("domaintwo.com"))
        self.assertEqual(lookup("domaintwo.com"), self.mail_server_domaintwo.id)

    def test_18_create_and_unlink_refresh_lookup(self):
        """Creating or deleting a server clears the cache."""
        self._init_mail_server_domain_whilelist_based()
        lookup = self.IrMailServer._get_mail_sever
        self.assertEqual(lookup("domainfive.com"), self.mail_server_domainone.id)

        new_server = self.IrMailServer.create(
            {
                "name": "sandbox domainfive",
                "smtp_host": "localhost",
                "domain_whitelist": "domainfive.com",
            }
        )
        self.assertFalse(self._is_lookup_cached("domainfive.com"))
        self.assertEqual(lookup("domainfive.com"), new_server.id)

        new_server.unlink()
        self.assertFalse(self._is_lookup_cached("domainfive.com"))
        self.assertEqual(lookup("domainfive.com"), self.mail_server_domainone.id)
