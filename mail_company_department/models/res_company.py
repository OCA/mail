# Copyright 2026 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    mail_ids = fields.One2many(
        "res.company.mail",
        "company_id",
        string="Department Emails",
    )

    def get_department_email(self, department):
        """Return the email configured for a department on this company.

        :param department: key of the department selection, e.g. "sale"
        :return: the email address, or False if none is configured
        """
        self.ensure_one()
        mail = self.mail_ids.filtered(lambda m: m.department == department)[:1]
        return mail.email or False
