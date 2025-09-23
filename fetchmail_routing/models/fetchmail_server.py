# © 2024 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class FetchmailServer(models.Model):
    _inherit = "fetchmail.server"

    @api.model
    def _fetch_mails(self):
        ret = super()._fetch_mails()
        self.env["mail.unassigned"].sudo().assign_mails()
        return ret
