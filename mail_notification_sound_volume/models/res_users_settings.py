# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResUsersSettings(models.Model):
    _inherit = "res.users.settings"

    notification_volume = fields.Float(default=1.0)
