# Copyright 2018-22 ForgeFlow <http://www.forgeflow.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import fields, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    keep_done = fields.Boolean(default=True)
