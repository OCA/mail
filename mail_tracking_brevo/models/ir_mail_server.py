# Copyright 2026 CIT-Services
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo import models


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    def _tracking_headers_add(self, tracking_email_id, headers):
        headers = super()._tracking_headers_add(tracking_email_id, headers)
        headers = headers or {}
        metadata = {
            "odoo_db": self.env.cr.dbname,
            "tracking_email_id": tracking_email_id,
        }
        headers["X-Mailin-custom"] = json.dumps(metadata)
        return headers
