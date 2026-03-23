# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    email_bcc = fields.Char(
        "Bcc", help="Blind cc recipients (placeholders may be used here)"
    )

    def _get_dynamic_field_names(self):
        res = super()._get_dynamic_field_names()
        res.add("email_bcc")
        return res
