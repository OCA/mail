# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo import fields, models


class FetchmailIncomingTestEml(models.TransientModel):
    _name = "fetchmail.incoming.test.eml"
    _inherit = "fetchmail.incoming.test.mixin"
    _description = "Simulate an Incoming Email from a File"

    eml_file = fields.Binary(
        string="Email File",
        required=True,
        attachment=False,
        help="Raw message, as exported by a mail client. Usually a .eml file.",
    )
    eml_filename = fields.Char()

    def _build_raw_message(self):
        # The file is fed to the gateway untouched: re-serializing a parsed
        # message would drop what makes a real mail worth replaying, such as
        # malformed HTML or unusual headers.
        self.ensure_one()
        return base64.b64decode(self.eml_file)
