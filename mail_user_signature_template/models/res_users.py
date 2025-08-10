# Copyright 2025 OCA Contributors
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import is_html_empty


class ResUsers(models.Model):
    _inherit = "res.users"

    use_signature_template = fields.Boolean(
        compute="_compute_use_signature_template",
        inverse="_inverse_use_signature_template",
        store=True,
        readonly=False,
        help="Use company signature template instead of custom signature",
    )
    _use_signature_template = fields.Boolean(
        string="Use Signature Template (stored)",
        help="Internal field to store user preference",
    )

    signature_template_id = fields.Many2one(
        "signature.template",
        string="Signature Template",
        compute="_compute_signature_template_id",
        inverse="_inverse_signature_template_id",
        store=True,
        readonly=False,
        domain="[('company_id', '=', company_id)]",
        help="Select a signature template to use",
    )
    _signature_template_id = fields.Many2one(
        "signature.template",
        string="Signature Template (stored)",
        help="Internal field to store user selection",
    )

    @api.depends(
        "company_id",
        "company_id.force_signature_template",
        "company_id.use_signature_templates",
        "_use_signature_template",
    )
    def _compute_use_signature_template(self):
        """Compute whether to use signature template based on company settings."""
        for user in self:
            if not user.company_id.use_signature_templates:
                user.use_signature_template = False
            elif user.company_id.force_signature_template:
                user.use_signature_template = True
            else:
                # Use stored preference or default to True for new users
                user.use_signature_template = (
                    user._use_signature_template
                    if user._use_signature_template is not None
                    else True
                )

    def _inverse_use_signature_template(self):
        """Store user preference for use_signature_template."""
        for user in self:
            if not user.company_id.force_signature_template:
                user._use_signature_template = user.use_signature_template

    @api.depends(
        "company_id",
        "company_id.use_signature_templates",
        "company_id.default_signature_template_id",
        "company_id.force_signature_template",
        "_signature_template_id",
    )
    def _compute_signature_template_id(self):
        """Compute signature template based on company settings."""
        for user in self:
            if (
                user.company_id.force_signature_template
                and user.company_id.default_signature_template_id
            ):
                user.signature_template_id = (
                    user.company_id.default_signature_template_id
                )
            elif user._signature_template_id:
                user.signature_template_id = user._signature_template_id
            elif (
                user.company_id.default_signature_template_id
                and not user._signature_template_id
            ):
                # Use company default if user hasn't selected one
                user.signature_template_id = (
                    user.company_id.default_signature_template_id
                )
            else:
                user.signature_template_id = False

    def _inverse_signature_template_id(self):
        """Store user selection for signature_template_id."""
        for user in self:
            if not user.company_id.force_signature_template:
                user._signature_template_id = user.signature_template_id

    @api.depends("signature_template_id", "use_signature_template", "name")
    def _compute_signature(self):
        """Override signature computation to use templates."""
        for user in self:
            if (
                user.use_signature_template
                and user.signature_template_id
                and user.company_id.use_signature_templates
            ):
                # Use template
                user.signature = user.signature_template_id._render_signature(user)
            elif (
                not user.use_signature_template
                and user.name
                and is_html_empty(user.signature)
            ):
                # Default signature only if no custom signature exists
                user.signature = f"<p>--<br />{user.name}</p>"
            # If signature already has value and not using template,
            # keep existing value (this is the custom signature)

    @api.model_create_multi
    def create(self, vals_list):
        """Set default values for new users."""
        for vals in vals_list:
            # Set default internal values if not provided
            if "_use_signature_template" not in vals:
                vals["_use_signature_template"] = True
            if "_signature_template_id" not in vals:
                company_id = vals.get("company_id") or self.env.company.id
                company = self.env["res.company"].browse(company_id)
                if (
                    company.use_signature_templates
                    and company.default_signature_template_id
                ):
                    vals["_signature_template_id"] = (
                        company.default_signature_template_id.id
                    )
        return super().create(vals_list)

    @api.onchange("company_id")
    def _onchange_company_id(self):
        """Update signature template when company changes."""
        if self.company_id:
            # Trigger recomputation of computed fields
            self._compute_use_signature_template()
            self._compute_signature_template_id()

    def write(self, vals):
        """Handle signature updates."""
        # Check if trying to change forced values
        for user in self:
            if user.company_id.force_signature_template:
                if "use_signature_template" in vals and not vals.get(
                    "use_signature_template"
                ):
                    raise ValidationError(
                        _("Cannot disable signature template when company forces it.")
                    )
                if (
                    "signature_template_id" in vals
                    and vals.get("signature_template_id")
                    != user.company_id.default_signature_template_id.id
                ):
                    raise ValidationError(
                        _(
                            "Cannot change signature template when company "
                            "forces a specific template."
                        )
                    )

        # Map computed fields to internal fields
        if "use_signature_template" in vals:
            for user in self:
                if not user.company_id.force_signature_template:
                    user._use_signature_template = vals.get("use_signature_template")
        if "signature_template_id" in vals:
            for user in self:
                if not user.company_id.force_signature_template:
                    user._signature_template_id = vals.get("signature_template_id")

        if "use_signature_template" in vals or "signature_template_id" in vals:
            # Force recomputation of signature
            vals["signature"] = False
        return super().write(vals)

    @api.model
    def _get_signature_access_fields(self):
        """Fields that users can modify on their own signature settings."""
        fields = []
        if hasattr(super(), "_get_signature_access_fields"):
            fields = super()._get_signature_access_fields()
        return fields + [
            "use_signature_template",
            "_use_signature_template",
            "signature_template_id",
            "_signature_template_id",
        ]

    def action_preview_signature(self):
        """Preview the current signature."""
        self.ensure_one()
        return {
            "name": "Signature Preview",
            "type": "ir.actions.act_window",
            "res_model": "signature.template.preview",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_user_id": self.id,
                "default_template_id": self.signature_template_id.id
                if self.signature_template_id
                else False,
            },
        }

    @api.model
    def mail_allowed_qweb_expressions(self):
        """Extend allowed QWeb expressions to include signature template variables.

        This is necessary for QWeb security - variables that are not in this list
        will cause the template to be rendered using regex fallback instead of
        the full QWeb engine, which doesn't have access to custom context variables.
        """
        # Get the base allowed expressions
        expressions = list(super().mail_allowed_qweb_expressions())

        # Don't add our custom variables here - they're not fields on res.users
        # They are context variables passed via add_context
        return tuple(expressions)

    def action_recompute_signature(self):
        """Manually trigger signature recomputation."""
        self._compute_signature()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _("Signature recomputed for %s user(s).") % len(self),
                "type": "success",
            },
        }
