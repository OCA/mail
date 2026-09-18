# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class IrModel(models.Model):
    _inherit = "ir.model"

    outgoing_mailserver_id = fields.Many2one(
        "ir.mail_server",
        help="""
    Allows to force the usage of a given outgoing mail server if this setting is set.
    However, this setting will be active only if the model extends `mail.thread`.
""",
    )
    outgoing_email = fields.Char(
        help="""
    Allows to force the usage of a given email address if this setting is set.
    However, this setting will be active only if the model extends `mail.thread`.
"""
    )
