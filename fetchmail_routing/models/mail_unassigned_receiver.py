# © 2024 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models
from odoo.tools.mail import formataddr

_logger = logging.getLogger(__name__)


class MailUnassignedReceiver(models.Model):
    _name = "mail.unassigned.receiver"
    _description = "Receiver of Unassigned E-Mails"

    mail_id = fields.Many2one("mail.unassigned", ondelete="cascade", required=True)
    type = fields.Selection([("to", "To"), ("cc", "CC")], required=True)
    name = fields.Char()
    email = fields.Char()

    @api.depends("name", "email")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = formataddr((rec.name or "", rec.email or ""))
