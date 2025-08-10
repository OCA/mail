# Copyright 2025 OCA Contributors
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SignatureTemplatePreview(models.TransientModel):
    _name = "signature.template.preview"
    _description = "Signature Template Preview"

    template_id = fields.Many2one(
        "signature.template",
        string="Template",
        required=False,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Preview for User",
        required=True,
        default=lambda self: self.env.user,
    )
    preview_html = fields.Html(
        string="Preview",
        compute="_compute_preview_html",
        readonly=True,
    )

    @api.depends("template_id", "user_id")
    def _compute_preview_html(self):
        for wizard in self:
            if wizard.template_id and wizard.user_id:
                wizard.preview_html = wizard.template_id._render_signature(
                    wizard.user_id
                )
            else:
                wizard.preview_html = False

    @api.onchange("user_id")
    def _onchange_user_id(self):
        """Update domain for template_id based on selected user's company."""
        if self.user_id:
            return {
                "domain": {
                    "template_id": [("company_id", "=", self.user_id.company_id.id)]
                }
            }
        return {"domain": {"template_id": []}}
