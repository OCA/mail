from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    mail_reply_stop_notification = fields.Boolean(
        string="Stop Email Notifications on Replies",
        help="If enabled, email notifications will not be sent to followers "
        "when a reply is received on a tracked email thread.",
        default=True,
    )
