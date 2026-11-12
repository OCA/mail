# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class MailScheduledMessage(models.Model):
    _inherit = "mail.scheduled.message"

    @api.model
    def _notification_parameters_whitelist(self):
        # Allow scheduling messages sent through the gateway composer
        return super()._notification_parameters_whitelist() | {"gateway_notifications"}
