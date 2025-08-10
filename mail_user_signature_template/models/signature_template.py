# Copyright 2025 OCA Contributors
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import re

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import html_sanitize, is_html_empty

_logger = logging.getLogger(__name__)


class SignatureTemplate(models.Model):
    _name = "signature.template"
    _description = "Email Signature Template"
    _order = "sequence, name"
    _inherit = ["mail.render.mixin"]

    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    # Template content
    body_html = fields.Html(
        string="Template",
        required=True,
        translate=True,
        render_engine="qweb",
        render_options={"post_process": True},
        sanitize=False,
        help="Design your signature template using QWeb syntax:\n"
        "- <t t-out='name'/>: User's display name\n"
        "- <t t-out='email'/>: User's email\n"
        "- <t t-out='phone'/>: User's phone number\n"
        "- <t t-out='mobile'/>: User's mobile number\n"
        "- <t t-out='function'/>: User's job position\n"
        "- <t t-out='company_name'/>: Company name\n"
        "- <t t-out='website'/>: Company website\n"
        "- <t t-out='website_url'/>: Website with UTM tracking\n"
        "- <t t-out='company_email'/>: Company email\n"
        "- <t t-out='company_phone'/>: Company phone\n"
        "- <t t-out='social_twitter'/>: Twitter URL\n"
        "- <t t-out='social_facebook'/>: Facebook URL\n"
        "- <t t-out='social_linkedin'/>: LinkedIn URL\n"
        "- <t t-out='social_instagram'/>: Instagram URL\n"
        "- <t t-out='social_youtube'/>: YouTube URL\n"
        "- <t t-out='social_github'/>: GitHub URL\n"
        "Use <t t-if='condition'> for conditionals\n"
        "Use <t t-out='company_logo'/> for company logo\n"
        "Use <t t-out='user_image'/> for user avatar (64x64)\n"
        "Use <t t-out='user_image_large'/> for larger avatar (116x116)\n"
        "Use <img t-att-src='user_image_url'/> for custom styled avatar\n"
        "Use <img t-att-src='user_image_url_large'/> for custom styled large avatar\n"
        "Use <t t-out='user_image_round'/> for circular avatar (64x64)\n"
        "Use <t t-out='user_image_large_round'/> for larger circular avatar (116x116)",
    )

    # Preview
    preview_html = fields.Html(
        string="Preview",
        compute="_compute_preview_html",
        help="Preview of the signature with current user's data",
    )
    preview_html_sanitized = fields.Html(
        string="Sanitized Preview",
        compute="_compute_preview_html",
        help="Preview of the signature after email sanitization",
    )

    # Template options
    include_company_logo = fields.Boolean(
        default=True,
        help="Add company logo to the signature",
    )
    logo_position = fields.Selection(
        [
            ("top", "Top"),
            ("left", "Left"),
            ("right", "Right"),
        ],
        default="left",
    )
    logo_max_width = fields.Integer(
        string="Logo Max Width (px)",
        default=150,
        help="Maximum width for the company logo in pixels",
    )
    use_company_colors = fields.Boolean(
        string="Use Company Email Colors",
        default=True,
        help="Use the company's email template colors (Header and Button colors) "
        "instead of custom colors",
    )
    primary_color = fields.Char(
        default="#0066cc",
        help="Primary accent color for links, avatars, and main elements (hex format)",
    )
    secondary_color = fields.Char(
        default="#ff6600",
        help="Secondary accent color for dividers, lines, and accents (hex format)",
    )

    # UTM Tracking
    use_utm_tracking = fields.Boolean(
        string="Use UTM Tracking",
        default=True,
        help="Add UTM parameters to links in the signature for tracking",
    )
    utm_campaign_id = fields.Many2one(
        "utm.campaign",
        string="Campaign",
        help="UTM Campaign for tracking email signature clicks",
    )
    utm_medium_id = fields.Many2one(
        "utm.medium",
        string="Medium",
        help="UTM Medium (defaults to 'email' if not set)",
    )
    utm_source_id = fields.Many2one(
        "utm.source",
        string="Source",
        help="UTM Source for tracking (e.g., 'email-signature')",
    )

    # Usage tracking
    user_count = fields.Integer(
        string="Users",
        compute="_compute_user_count",
        help="Number of users using this template",
    )

    @api.depends("body_html")
    def _compute_preview_html(self):
        for template in self:
            if template.body_html:
                rendered = template._render_signature(self.env.user)
                template.preview_html = rendered

                # Apply sanitization for the sanitized preview
                template.preview_html_sanitized = html_sanitize(
                    rendered,
                    sanitize_tags=False,
                    sanitize_attributes=False,
                    sanitize_style=True,
                    strip_style=False,
                    strip_classes=False,
                )
            else:
                template.preview_html = False
                template.preview_html_sanitized = False

    def _compute_user_count(self):
        for template in self:
            template.user_count = self.env["res.users"].search_count(
                [
                    ("signature_template_id", "=", template.id),
                    ("use_signature_template", "=", True),
                ]
            )

    @api.constrains("body_html")
    def _check_body_html(self):
        for template in self:
            if is_html_empty(template.body_html):
                raise ValidationError(_("Template content cannot be empty."))

    def _build_utm_url(self, base_url, user=None):
        """Build URL with UTM parameters if tracking is enabled."""
        if not self.use_utm_tracking or not base_url:
            return base_url

        # Clean up the URL first - remove any duplicate protocols
        base_url = base_url.strip()

        # Handle cases like "https://https://example.com"
        if base_url.startswith("https://https://"):
            base_url = base_url[8:]  # Remove first "https://"
        elif base_url.startswith("http://http://"):
            base_url = base_url[7:]  # Remove first "http://"
        elif base_url.startswith("https://http://"):
            base_url = base_url[8:]  # Remove "https://" and keep "http://"
        elif base_url.startswith("http://https://"):
            base_url = base_url[7:]  # Remove "http://" and keep "https://"

        # Ensure URL has protocol
        if not base_url.startswith(("http://", "https://")):
            base_url = "https://" + base_url

        # Parse URL
        from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

        parsed = urlparse(base_url)
        params = parse_qs(parsed.query)

        # Add UTM parameters
        if self.utm_source_id:
            params["utm_source"] = [self.utm_source_id.name]
        else:
            params["utm_source"] = ["email-signature"]

        if self.utm_medium_id:
            params["utm_medium"] = [self.utm_medium_id.name]
        else:
            params["utm_medium"] = ["email"]

        if self.utm_campaign_id:
            params["utm_campaign"] = [self.utm_campaign_id.name]

        # Add user info as utm_content for granular tracking
        if user:
            params["utm_content"] = [f"user-{user.id}"]

        # Rebuild URL
        new_query = urlencode(params, doseq=True)
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )

    def _get_render_values(self, user):  # noqa: C901
        """Get values for rendering the signature template."""
        values = {
            "name": user.name or "",
            "email": user.email or "",
            "phone": user.phone or "",
            "mobile": user.mobile or "",
            "function": user.function or "",
            "company_name": user.company_id.name or "",
            "website": user.company_id.website or "",
            "company_email": user.company_id.email or "",
            "company_phone": user.company_id.phone or "",
            "primary_color": (
                user.company_id.email_primary_color
                if self.use_company_colors
                else self.primary_color
            )
            or "#0066cc",
            "secondary_color": (
                user.company_id.email_secondary_color
                if self.use_company_colors
                else self.secondary_color
            )
            or "#ff6600",
            "divider_color": (
                user.company_id.email_primary_color
                if self.use_company_colors
                else self.primary_color
            )
            or "#0066cc",  # Backward compatibility
        }

        # Build website URL with UTM tracking or just clean it up
        if user.company_id.website:
            if self.use_utm_tracking:
                values["website_url"] = self._build_utm_url(
                    user.company_id.website, user
                )
            else:
                # Even without UTM, we should clean up the URL
                website = user.company_id.website.strip()
                # Handle duplicate protocols
                if website.startswith("https://https://"):
                    website = website[8:]
                elif website.startswith("http://http://"):
                    website = website[7:]
                elif website.startswith("https://http://"):
                    website = website[8:]
                elif website.startswith("http://https://"):
                    website = website[7:]
                # Add protocol if missing
                if not website.startswith(("http://", "https://")):
                    website = "https://" + website
                values["website_url"] = website
        else:
            values["website_url"] = ""

        # Add user avatar URL using res.users avatar fields (which have fallback)
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        # Use avatar fields which provide fallback when no photo is uploaded
        # Provide URLs for custom styling
        values["user_avatar_url"] = (
            f"{base_url}/web/image/res.users/{user.id}/avatar_128"
        )
        values["user_avatar_url_large"] = (
            f"{base_url}/web/image/res.users/{user.id}/avatar_256"
        )

        # Import controller to get public URLs
        from ..controllers.public_image import PublicSignatureImage

        # avatar_128 for smaller circular avatars (use public URL)
        avatar_url = PublicSignatureImage.get_public_avatar_url(
            user.id, size="128", env=self.env
        )
        values["user_image"] = Markup(
            f'<img src="{avatar_url}" '
            f'alt="{user.name}" '
            f'width="64" height="64" '
            f'style="display:block;border:0;object-fit:cover;" />'
        )
        # avatar_256 for larger avatars in templates (use public URL)
        avatar_url_large = PublicSignatureImage.get_public_avatar_url(
            user.id, size="256", env=self.env
        )
        values["user_image_large"] = Markup(
            f'<img src="{avatar_url_large}" '
            f'alt="{user.name}" '
            f'width="116" height="116" '
            f'style="display:block;object-fit:cover;border:0;" />'
        )

        # Circular versions with border-radius
        values["user_image_round"] = Markup(
            f'<img src="{avatar_url}" '
            f'alt="{user.name}" '
            f'width="64" height="64" '
            f'style="display:block;border-radius:50%;border:0;object-fit:cover;" />'
        )
        values["user_image_large_round"] = Markup(
            f'<img src="{avatar_url_large}" '
            f'alt="{user.name}" '
            f'width="116" height="116" '
            f'style="display:block;border-radius:50%;object-fit:cover;border:0;" />'
        )

        # Just the avatar URL for custom styling in templates
        values["user_image_url"] = avatar_url
        values["user_image_url_large"] = avatar_url_large

        # Add company logo if enabled
        if self.include_company_logo:
            company = user.company_id
            width = company.signature_logo_width or 120
            style = (
                "display:block;border:0;outline:none;text-decoration:none;"
                f"max-width:{self.logo_max_width}px;height:auto;"
            )

            if company.signature_logo_url:
                # Use custom external URL if provided (override)
                values["company_logo"] = Markup(
                    f'<img src="{company.signature_logo_url}" '
                    f'alt="{company.name}" '
                    f'width="{width}" '
                    f'style="{style}" />'
                )
            elif company.logo:
                # Use public URL for company logo to work with Gmail proxy
                logo_url = PublicSignatureImage.get_public_logo_url(
                    company.id, env=self.env
                )
                values["company_logo"] = Markup(
                    f'<img src="{logo_url}" '
                    f'alt="{company.name}" '
                    f'width="{width}" '
                    f'style="{style}" />'
                )
            else:
                values["company_logo"] = ""
        else:
            values["company_logo"] = ""

        # Add social media URLs using Odoo's /website/social/<platform> routes
        # This provides built-in tracking and proper redirects
        company = user.company_id
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")

        # Make base_url available in templates for absolute paths
        values["base_url"] = base_url

        social_platforms = {
            "social_twitter": "twitter",
            "social_facebook": "facebook",
            "social_linkedin": "linkedin",
            "social_instagram": "instagram",
            "social_youtube": "youtube",
            "social_github": "github",
        }

        for field, platform in social_platforms.items():
            # Check if field exists on company (provided by social_media module)
            if hasattr(company, field):
                social_value = getattr(company, field, "")
                if social_value:
                    # If website module is installed, use social redirect URL
                    if self.env.registry.get("website"):
                        social_url = f"{base_url}/website/social/{platform}"
                        if self.use_utm_tracking:
                            values[field] = self._build_utm_url(social_url, user)
                        else:
                            values[field] = social_url
                    else:
                        # Direct URL without redirect
                        if self.use_utm_tracking:
                            values[field] = self._build_utm_url(social_value, user)
                        else:
                            values[field] = social_value
                else:
                    values[field] = ""
            else:
                values[field] = ""

        return values

    def _render_signature(self, user):
        """Render the signature template for a specific user."""
        self.ensure_one()
        if not self.body_html:
            return ""

        values = self._get_render_values(user)

        # Use qweb engine with proper QWeb syntax
        rendered = self._render_template(
            self.body_html,
            "res.users",
            user.ids,
            engine="qweb",
            add_context=values,
        )[user.id]

        # Wrap in signature div
        return f'<div class="o_mail_signature">{rendered}</div>'

    @api.model
    def create_default_template(self):
        """Create a default signature template."""
        return self.create(
            {
                "name": _("Default Signature Template"),
                "body_html": """
                <table style="font-family: Arial, sans-serif; font-size: 14px;
                              color: #333;">
                    <tr>
                        <td style="padding-right: 20px;">
                            <t t-out="company_logo"/>
                        </td>
                        <td>
                            <div style="margin-bottom: 5px;">
                                <strong><t t-out="name"/></strong><br/>
                                <span style="color: #666;"><t t-out="function"/></span>
                            </div>
                            <div style="margin-bottom: 5px;">
                                <span><t t-out="company_name"/></span>
                            </div>
                            <div style="font-size: 12px; color: #666;">
                                <t t-out="email"/><br/>
                                <t t-out="phone"/><br/>
                                <t t-out="website"/>
                            </div>
                        </td>
                    </tr>
                </table>
            """,
            }
        )

    def action_preview(self):
        """Open a wizard to preview the signature with different users."""
        self.ensure_one()
        return {
            "name": _("Preview Signature Template"),
            "type": "ir.actions.act_window",
            "res_model": "signature.template.preview",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_template_id": self.id,
                "default_user_id": self.env.user.id,
            },
        }

    def action_view_users(self):
        """View users using this template."""
        self.ensure_one()
        return {
            "name": _("Users"),
            "type": "ir.actions.act_window",
            "res_model": "res.users",
            "view_mode": "list,form",
            "domain": [
                ("signature_template_id", "=", self.id),
                ("use_signature_template", "=", True),
            ],
        }

    def write(self, vals):
        """Override write to invalidate user signatures when template changes."""
        res = super().write(vals)

        # Check if any field that affects rendering has changed
        if any(
            field in vals
            for field in [
                "body_html",
                "include_company_logo",
                "logo_position",
                "primary_color",
                "secondary_color",
                "use_company_colors",
                "use_utm_tracking",
                "utm_source_id",
                "utm_medium_id",
                "utm_campaign_id",
            ]
        ):
            # Find all users using these templates
            users = self.env["res.users"].search(
                [
                    ("use_signature_template", "=", True),
                    ("signature_template_id", "in", self.ids),
                ]
            )
            if users:
                # Force recomputation of signatures
                users._compute_signature()

        return res

    def _get_style_whitelist(self):
        """Get the list of allowed CSS properties from Odoo's sanitizer."""
        # Import and use Odoo's actual _Cleaner class to stay in sync
        from odoo.tools.mail import _Cleaner

        return _Cleaner._style_whitelist

    def _get_sanitization_report(self):
        """Analyze rendered template output and return detailed sanitization report."""
        self.ensure_one()

        report = {
            "changes_detected": False,
            "original_html": "",
            "sanitized_html": "",
            "sanitization_contexts": [],
        }

        if not self.body_html:
            return report

        try:
            # Render template first to process QWeb
            rendered = self._render_signature(self.env.user)
            report["original_html"] = rendered

            # Test different sanitization contexts
            contexts = [
                {
                    "name": "Email Composer (Default)",
                    "params": {
                        "sanitize_tags": False,
                        "sanitize_attributes": False,
                        "sanitize_style": True,
                        "strip_style": False,
                        "strip_classes": False,
                    },
                },
                {
                    "name": "Chatter Messages",
                    "params": {
                        "sanitize_tags": False,
                        "sanitize_attributes": False,
                        "sanitize_style": True,
                        "strip_style": False,
                        "strip_classes": True,  # Note: classes are stripped in chatter
                    },
                },
            ]

            for context in contexts:
                sanitized = html_sanitize(rendered, **context["params"])
                context["sanitized_html"] = sanitized
                context["changed"] = rendered != sanitized

                if context["changed"]:
                    report["changes_detected"] = True
                    # Simple diff - just check if styles were removed
                    context["diff_summary"] = self._get_simple_diff_summary(
                        rendered, sanitized
                    )

                report["sanitization_contexts"].append(context)

            # Use the default context for the main sanitized version
            report["sanitized_html"] = report["sanitization_contexts"][0][
                "sanitized_html"
            ]

        except Exception as e:
            _logger.warning(f"Error analyzing sanitization: {e}")
            report["error"] = str(e)

        return report

    def _get_simple_diff_summary(self, original, sanitized):
        """Get a simple summary of what changed between original and sanitized HTML."""
        summary = []
        issues_found = {}

        # Check for removed styles
        from lxml import html as lhtml

        try:
            # Parse both HTML strings
            orig_tree = lhtml.fromstring(original)
            san_tree = lhtml.fromstring(sanitized)

            # Compare style attributes
            san_styles = {
                elem: elem.get("style", "")
                for elem in san_tree.iter()
                if elem.get("style")
            }

            # Analyze specific removed properties
            removed_properties = set()
            for elem in orig_tree.iter():
                if elem.get("style"):
                    orig_style = elem.get("style", "")
                    # Parse the style properties
                    prop_pattern = re.compile(r"([\w-]+)\s*:\s*([^;]+)")
                    properties = prop_pattern.findall(orig_style)

                    for prop_name, prop_value in properties:
                        prop_name = prop_name.strip().lower()
                        # Check common issues
                        if (
                            "border-right" in prop_name
                            and "border-right-" not in prop_name
                        ):
                            issues_found["border-shorthand"] = True
                        elif "font-family" in prop_name and "," in prop_value:
                            issues_found["font-family-list"] = True
                        elif prop_name == "background" and (
                            "gradient" in prop_value or "#" in prop_value
                        ):
                            issues_found["background-shorthand"] = True
                        elif prop_name in ["letter-spacing", "outline"]:
                            removed_properties.add(prop_name)

            # Build summary with suggestions
            if issues_found.get("border-shorthand"):
                summary.append(
                    "❌ Border shorthand detected - use individual properties"
                )
            if issues_found.get("font-family-list"):
                summary.append("❌ Font family lists may be stripped - use single font")
            if issues_found.get("background-shorthand"):
                summary.append(
                    "❌ Background shorthand/gradients detected - use background-color"
                )
            if "letter-spacing" in removed_properties:
                summary.append(
                    "❌ letter-spacing is not allowed - adjust font-size instead"
                )
            if "outline" in removed_properties:
                summary.append("❌ outline is not allowed - use border instead")

            # Count total changes
            style_changes = len(
                [
                    1
                    for elem in orig_tree.iter()
                    if elem.get("style")
                    and not any(elem.get("style") in s for s in san_styles.values())
                ]
            )
            if style_changes > len(summary):
                summary.append(
                    f"... and {style_changes - len(summary)} more style changes"
                )

        except Exception as e:
            summary.append(f"Could not analyze differences: {str(e)}")

        return summary

    def _format_sanitization_report(self, report):
        """Format the sanitization report as HTML for display."""
        if report.get("error"):
            return (
                '<div class="alert alert-danger">'
                '<i class="fa fa-exclamation-circle"></i> '
                f'Error: {report["error"]}'
                '</div>'
            )

        if not report.get("changes_detected"):
            return (
                '<p class="text-success">'
                '<i class="fa fa-check-circle"></i> '
                "No sanitization issues detected. "
                "Your signature will be sent as-is."
                "</p>"
            )

        html_parts = []

        # Show different sanitization contexts
        for context in report.get("sanitization_contexts", []):
            if context.get("changed"):
                html_parts.append('<div class="alert alert-warning">')
                html_parts.append(
                    '<h5><i class="fa fa-exclamation-triangle"></i> '
                    f'{context["name"]}</h5>'
                )

                if context.get("diff_summary"):
                    html_parts.append("<ul>")
                    for change in context["diff_summary"]:
                        html_parts.append(f"<li>{change}</li>")
                    html_parts.append("</ul>")
                else:
                    html_parts.append(
                        "<p>Content will be modified but no specific "
                        "changes detected.</p>"
                    )

                html_parts.append("</div>")

        # Add comprehensive solutions section
        if report.get("changes_detected"):
            html_parts.append('<div class="alert alert-info">')
            html_parts.append(
                '<h5><i class="fa fa-lightbulb-o"></i> Solutions for Common Issues</h5>'
            )

            # Check what issues were found
            all_summaries = " ".join(
                str(c.get("diff_summary", []))
                for c in report.get("sanitization_contexts", [])
            )

            if "border" in all_summaries or "border-right" in all_summaries:
                html_parts.append("<h6>Border Properties:</h6>")
                html_parts.append("<ul>")
                html_parts.append(
                    "<li>Replace <code>border-right: 1px solid #ddd</code> with:<br/>"
                )
                html_parts.append(
                    "<code>border-right-width: 1px; "
                    "border-right-style: solid; "
                    "border-right-color: #ddd;</code></li>"
                )
                html_parts.append("</ul>")

            if "font-family" in all_summaries:
                html_parts.append("<h6>Font Families:</h6>")
                html_parts.append("<ul>")
                html_parts.append("<li>Use a single font instead of font stacks</li>")
                html_parts.append(
                    "<li>Replace <code>font-family: -apple-system, "
                    "BlinkMacSystemFont, ...</code><br/>"
                )
                html_parts.append(
                    "with <code>font-family: Arial, sans-serif;</code></li>"
                )
                html_parts.append("</ul>")

            if "background" in all_summaries or "gradient" in all_summaries:
                html_parts.append("<h6>Backgrounds:</h6>")
                html_parts.append("<ul>")
                html_parts.append(
                    "<li>Use <code>background-color</code> instead of "
                    "<code>background</code> shorthand</li>"
                )
                html_parts.append(
                    "<li>Gradients are not supported - use solid colors</li>"
                )
                html_parts.append(
                    "<li>Replace <code>background: #color "
                    "linear-gradient(...)</code><br/>"
                )
                html_parts.append("with <code>background-color: #color;</code></li>")
                html_parts.append("</ul>")

            if "letter-spacing" in all_summaries:
                html_parts.append("<h6>Typography:</h6>")
                html_parts.append("<ul>")
                html_parts.append(
                    "<li><code>letter-spacing</code> is not allowed - "
                    "adjust <code>font-size</code> instead</li>"
                )
                html_parts.append(
                    "<li><code>outline</code> is not allowed - "
                    "use <code>border</code> instead</li>"
                )
                html_parts.append("</ul>")

            html_parts.append("<h6>General Tips:</h6>")
            html_parts.append("<ul>")
            html_parts.append("<li>Use table-based layouts for complex designs</li>")
            html_parts.append("<li>Test in multiple email clients</li>")
            html_parts.append("<li>Keep styles simple and inline</li>")
            html_parts.append("</ul>")

            html_parts.append("</div>")

        return Markup("".join(html_parts))

    def action_check_sanitization(self):
        """Action to check template sanitization and show report in a wizard."""
        self.ensure_one()

        try:
            # Get sanitization report
            report = self._get_sanitization_report()
            has_issues = bool(report.get("removed_styles") or report.get("warnings"))

            # Format the report as HTML
            report_html = self._format_sanitization_report(report)

            # Try to create wizard with report
            wizard = self.env["signature.sanitization.check"].create(
                {
                    "template_id": self.id,
                    "has_issues": report.get("changes_detected", False),
                    "report_html": report_html,
                    "original_html": report.get("original_html", ""),
                    "sanitized_html": report.get("sanitized_html", ""),
                }
            )

            return {
                "name": _("Sanitization Check Results"),
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "res_model": "signature.sanitization.check",
                "res_id": wizard.id,
                "target": "new",
                "context": {"dialog_size": "large"},
            }
        except Exception as e:
            # If wizard fails, fall back to notification
            _logger.warning(f"Failed to create sanitization wizard: {e}")

            # Get sanitization report
            report = self._get_sanitization_report()
            has_issues = bool(report.get("removed_styles") or report.get("warnings"))

            # Format the report as HTML message
            if has_issues:
                report_html = self._format_sanitization_report(report)
                message = (
                    _(
                        "Template contains styles that will be removed "
                        "during email sending.<br/><br/>"
                    )
                    + report_html
                )
                msg_type = "warning"
            else:
                message = _(
                    '<i class="fa fa-check-circle"></i> '
                    "Template passes all sanitization checks!<br/>"
                    "No styles will be removed during email sending."
                )
                msg_type = "success"

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Sanitization Check Results"),
                    "message": message,
                    "type": msg_type,
                    "sticky": True,
                },
            }
