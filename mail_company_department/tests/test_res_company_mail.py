# Copyright 2026 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase
from odoo.tools import mute_logger


class TestResCompanyMail(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.Mail = cls.env["res.company.mail"]

    def test_create_valid_email(self):
        """A valid address on a department is stored as given."""
        mail = self.Mail.create(
            {"department": "sale", "email": "sales@example.com"}
        )
        self.assertEqual(mail.company_id, self.company)
        self.assertEqual(mail.email, "sales@example.com")

    def test_invalid_email_raises(self):
        """A malformed address is rejected with a ValidationError."""
        with self.assertRaises(ValidationError):
            self.Mail.create({"department": "sale", "email": "not-an-email"})

    def test_multiple_addresses_raise(self):
        """Several addresses in one field are rejected (strict check)."""
        with self.assertRaises(ValidationError):
            self.Mail.create(
                {"department": "sale", "email": "a@example.com, b@example.com"}
            )

    @mute_logger("odoo.sql_db")
    def test_one_email_per_department(self):
        """A company cannot have two emails for the same department."""
        self.Mail.create({"department": "purchase", "email": "p1@example.com"})
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.Mail.create({"department": "purchase", "email": "p2@example.com"})

    def test_get_department_email_returns_configured(self):
        """get_department_email returns the address configured for the department."""
        self.Mail.create({"department": "accounting", "email": "acc@example.com"})
        self.assertEqual(
            self.company.get_department_email("accounting"), "acc@example.com"
        )

    def test_get_department_email_missing_returns_false(self):
        """get_department_email returns False when no address is configured."""
        self.assertFalse(self.company.get_department_email("logistics"))
