# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailComposer(models.TransientModel):
    _inherit = "mail.compose.message"

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        template_id = values.get("template_id")
        template = self.env["mail.template"].browse(template_id)
        # OVERRIDE to force the email_layout_xmlid defined on the mail.template.
        # The _compute_email_layout_xmlid method is not triggered at initialization
        # when there is a default value from context, so we override it here.
        if template and template.email_layout_xmlid:
            values["email_layout_xmlid"] = template.email_layout_xmlid
        return values
