# Copyright 2026 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import email_normalize

DEPARTMENT_SELECTION = [
    ("sale", "Sales"),
    ("purchase", "Purchase"),
    ("accounting", "Accounting"),
    ("logistics", "Logistics"),
    ("support", "Customer Support"),
]


class ResCompanyMail(models.Model):
    _name = "res.company.mail"
    _description = "Company Department Email"
    _order = "company_id, department"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        ondelete="cascade",
        index=True,
        default=lambda self: self.env.company,
    )
    department = fields.Selection(
        DEPARTMENT_SELECTION,
        required=True,
    )
    email = fields.Char(required=True)

    _sql_constraints = [
        (
            "company_department_uniq",
            "UNIQUE(company_id, department)",
            "Each department can have only one email per company.",
        ),
    ]

    @api.constrains("email")
    def _check_email(self):
        """Ensure the email holds exactly one valid address."""
        for rec in self:
            if not email_normalize(rec.email, strict=True):
                raise ValidationError(
                    self.env._("'%s' is not a valid email address.") % rec.email
                )
