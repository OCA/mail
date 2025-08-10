# Copyright 2025 OCA Contributors
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    use_signature_templates = fields.Boolean(
        default=True,
        help="Enable company-wide signature templates for users",
    )

    default_signature_template_id = fields.Many2one(
        "signature.template",
        string="Default Signature Template",
        help="Default signature template for new users",
    )

    force_signature_template = fields.Boolean(
        default=False,
        help="If enabled, users cannot override the signature template",
    )

    signature_logo_url = fields.Char(
        string="Signature Logo URL (Override)",
        help="Optional: External URL to override the default company logo in "
        "signatures. If not set, Odoo will use the company logo from Settings. "
        "(e.g., https://cdn.company.com/logo-email.png)",
    )

    signature_logo_width = fields.Integer(
        string="Logo Display Width",
        default=120,
        help="Display width of the logo in email signatures (pixels). "
        "Height will be automatically adjusted to maintain aspect ratio.",
    )

    @api.onchange("default_signature_template_id")
    def _onchange_default_signature_template_id(self):
        """Ensure the selected template belongs to this company."""
        if self.default_signature_template_id and self.id:
            if self.default_signature_template_id.company_id != self:
                self.default_signature_template_id = False
                return {
                    "domain": {
                        "default_signature_template_id": [("company_id", "=", self.id)]
                    }
                }
        return {
            "domain": {
                "default_signature_template_id": [("company_id", "=", self.id)]
                if self.id
                else []
            }
        }

    def write(self, vals):
        """Override write to invalidate user signatures when company fields change."""
        res = super().write(vals)

        # Check if any field that affects signature rendering has changed
        signature_fields = [
            "logo",
            "website",
            "email",
            "phone",
            "email_primary_color",
            "email_secondary_color",
            "signature_logo_url",
            "signature_logo_width",
        ]

        # Add social media fields if they exist
        social_fields = [
            "social_twitter",
            "social_facebook",
            "social_linkedin",
            "social_instagram",
            "social_youtube",
            "social_github",
        ]
        for field in social_fields:
            if field in self._fields:
                signature_fields.append(field)

        if any(field in vals for field in signature_fields):
            # Find all users in these companies using signature templates
            users = self.env["res.users"].search(
                [
                    ("use_signature_template", "=", True),
                    ("company_id", "in", self.ids),
                ]
            )
            if users:
                # Force recomputation of signatures
                users._compute_signature()

        return res
