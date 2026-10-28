# Copyright 2026 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    post_in_queue_job = fields.Boolean(
        string="Post in a Queue Job",
        help="Messages posted automatically with this template (for example, an "
        "order or delivery confirmation) are rendered and sent in a queue job, "
        "so the user does not wait for them.",
    )
