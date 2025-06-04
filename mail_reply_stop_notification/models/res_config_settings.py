from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mail_reply_stop_notification = fields.Boolean(
        related="company_id.mail_reply_stop_notification",
        readonly=False,
    )
