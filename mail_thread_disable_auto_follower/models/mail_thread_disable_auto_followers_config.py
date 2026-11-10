# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailThreadDisableAutoFollowersConfig(models.Model):
    _name = "mail.thread.disable.auto.followers.config"
    _description = "Disable Auto Followers Configuration"

    name = fields.Char(default="Configuration", required=True, readonly=True)
    model_ids = fields.Many2many(
        "ir.model",
        string="Disabled Models",
        domain=[("model", "!=", False)],
    )
