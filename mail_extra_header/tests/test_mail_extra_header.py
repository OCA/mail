# Copyright 2024 Camptocamp SA (https://www.camptocamp.com).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from textwrap import dedent

from odoo.exceptions import ValidationError

from odoo.addons.base.tests.common import BaseCommon


class TestMailExtraHeader(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test mail servers with different configurations
        cls.mail_server_1 = cls.env["ir.mail_server"].create(
            {
                "name": "Test Server 1",
                "smtp_host": "smtp.test1.com",
                "smtp_port": 587,
                "smtp_user": "user1@test1.com",
                "smtp_pass": "password1",
                "from_filter": "test1.com",
                "extra_headers": dedent(
                    """
                    {
                        'X-Custom-Header-1': 'value1',
                        'X-Priority': 'high',
                    }
                    """
                ),
            }
        )
        cls.mail_server_2 = cls.env["ir.mail_server"].create(
            {
                "name": "Test Server 2",
                "smtp_host": "smtp.test2.com",
                "smtp_port": 587,
                "smtp_user": "user2@test2.com",
                "smtp_pass": "password2",
                "from_filter": "test2.com",
                "extra_headers": dedent(
                    """
                    {
                        'X-Custom-Header-2': 'value2',
                        'X-Importance': 'urgent',
                    }
                    """
                ),
            }
        )
        cls.mail_server_3 = cls.env["ir.mail_server"].create(
            {
                "name": "Test Server 3",
                "smtp_host": "smtp.test3.com",
                "smtp_port": 587,
                "smtp_user": "user3@test3.com",
                "smtp_pass": "password3",
                "from_filter": "test3.com",
            }
        )

    def test_extra_headers_validation_invalid_syntax(self):
        """Test that invalid syntax raises ValidationError"""
        with self.assertRaisesRegex(
            ValidationError, r"The extra headers cannot be read \(syntax error\)\."
        ):
            self.env["ir.mail_server"].create(
                {
                    "name": "Invalid Server",
                    "smtp_host": "smtp.invalid.com",
                    # Missing closing brace
                    "extra_headers": "{'X-Test': 'value', 'X-Another': 'another_value'",
                }
            )

    def test_extra_headers_validation_not_dict(self):
        """Test that non-dictionary values raise ValidationError"""
        with self.assertRaisesRegex(
            ValidationError, r"The extra headers must be a dictionary of strings\."
        ):
            self.env["ir.mail_server"].create(
                {
                    "name": "Invalid Server",
                    "smtp_host": "smtp.invalid.com",
                    "extra_headers": "['not', 'a', 'dict']",
                }
            )

    def test_extra_headers_validation_not_dict_of_strings(self):
        """Test that non-dictionary values raise ValidationError"""
        with self.assertRaisesRegex(
            ValidationError, r"The extra headers must be a dictionary of strings\."
        ):
            self.mail_server_1.extra_headers = "{'X-CUSTOM-HEADER': [1, 2, 3]}"

    def test_sending_with_extra_headers_server_1(self):
        """Test that sending a mail with server 1 has the correct extra headers"""
        message = self.env["ir.mail_server"].build_email(
            ["sender@test1.com"],
            ["recipient@example.com"],
            "Test Subject",
            "Test Body",
        )
        # Send email using server 1
        self.env["ir.mail_server"].send_email(
            message, mail_server_id=self.mail_server_1.id
        )
        # Check that the correct headers are added
        self.assertEqual(message["X-Custom-Header-1"], "value1")
        self.assertEqual(message["X-Priority"], "high")
        # Check that server 2 headers are not present
        self.assertNotIn("X-Custom-Header-2", message)
        self.assertNotIn("X-Importance", message)

    def test_sending_with_extra_headers_server_2(self):
        """Test that sending a mail with server 2 has the correct extra headers"""
        message = self.env["ir.mail_server"].build_email(
            ["sender@test2.com"],
            ["recipient@example.com"],
            "Test Subject",
            "Test Body",
        )
        # Send email using server 2
        self.env["ir.mail_server"].send_email(
            message, mail_server_id=self.mail_server_2.id
        )
        # Check that the correct headers are added
        self.assertEqual(message["X-Custom-Header-2"], "value2")
        self.assertEqual(message["X-Importance"], "urgent")
        # Check that server 1 headers are not present
        self.assertNotIn("X-Custom-Header-1", message)
        self.assertNotIn("X-Priority", message)

    def test_sending_with_extra_headers_server_3(self):
        """Test that sending a mail with server 3 (empty headers) doesn't add any"""
        message = self.env["ir.mail_server"].build_email(
            ["sender@test3.com"],
            ["recipient@example.com"],
            "Test Subject",
            "Test Body",
        )
        # Send email using server 3
        self.env["ir.mail_server"].send_email(
            message, mail_server_id=self.mail_server_3.id
        )
        # Check that no extra headers are added
        self.assertNotIn("X-Custom-Header-1", message)
        self.assertNotIn("X-Custom-Header-2", message)
        self.assertNotIn("X-Priority", message)
        self.assertNotIn("X-Importance", message)

    def test_sending_with_from_filter_detection(self):
        """Test that the correct server is selected based on From address"""
        # Test with server 1's from_filter
        message = self.env["ir.mail_server"].build_email(
            ["sender@test1.com"],
            ["recipient@example.com"],
            "Test Subject",
            "Test Body",
        )
        # Send email without specifying mail_server_id (should auto-detect)
        self.env["ir.mail_server"].send_email(message)
        # Check that server 1 headers are added
        self.assertEqual(message["X-Custom-Header-1"], "value1")
        self.assertEqual(message["X-Priority"], "high")

    def test_sending_with_from_filter_detection_server_2(self):
        """Test that the correct server is selected based on From address"""
        # Test with server 2's from_filter
        message = self.env["ir.mail_server"].build_email(
            ["sender@test2.com"],
            ["recipient@example.com"],
            "Test Subject",
            "Test Body",
        )
        # Send email without specifying mail_server_id (should auto-detect)
        self.env["ir.mail_server"].send_email(message)
        # Check that server 2 headers are added
        self.assertEqual(message["X-Custom-Header-2"], "value2")
        self.assertEqual(message["X-Importance"], "urgent")
