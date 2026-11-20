from odoo import fields, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    message_partner_ids = fields.Many2many(
        domain=lambda thread: thread.env[
            "mail.followers.edit"
        ]._mail_restrict_follower_selection_get_domain(thread._name)
    )
