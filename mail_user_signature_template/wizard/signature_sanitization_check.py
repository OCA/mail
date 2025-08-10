# Copyright 2025 OCA Contributors
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from markupsafe import Markup

from odoo import _, fields, models
from odoo.tools.misc import get_diff


class SignatureSanitizationCheck(models.TransientModel):
    _name = "signature.sanitization.check"
    _description = "Signature Template Sanitization Check"

    template_id = fields.Many2one(
        "signature.template", string="Template", required=True, readonly=True
    )
    template_name = fields.Char(
        related="template_id.name", string="Template Name", readonly=True
    )
    has_issues = fields.Boolean(readonly=True)
    report_html = fields.Html(
        string="Sanitization Report", readonly=True, sanitize=False
    )
    original_html = fields.Html(string="Original HTML", readonly=True, sanitize=False)
    sanitized_html = fields.Html(string="Sanitized HTML", readonly=True, sanitize=False)
    diff_html = fields.Html(
        readonly=True,
        sanitize=False,
        compute="_compute_diff_html",
    )

    def _compute_diff_html(self):
        """Compute HTML diff between original and sanitized."""
        for wizard in self:
            if wizard.has_issues and wizard.original_html and wizard.sanitized_html:
                try:
                    # Try to use BeautifulSoup if available for better formatting
                    from bs4 import BeautifulSoup

                    # Pretty print the HTML for better diff visualization
                    orig_soup = BeautifulSoup(wizard.original_html, "html.parser")
                    san_soup = BeautifulSoup(wizard.sanitized_html, "html.parser")

                    orig_pretty = orig_soup.prettify()
                    san_pretty = san_soup.prettify()

                    # Get the diff table using Odoo's function
                    diff_table = get_diff(
                        (orig_pretty, _("Original")),
                        (san_pretty, _("After Sanitization")),
                        dark_color_scheme=False,
                    )

                    wizard.diff_html = Markup(diff_table)
                except ImportError:
                    # BeautifulSoup not available, use raw HTML
                    diff_table = get_diff(
                        (wizard.original_html, _("Original")),
                        (wizard.sanitized_html, _("After Sanitization")),
                        dark_color_scheme=False,
                    )
                    wizard.diff_html = Markup(diff_table)
            else:
                wizard.diff_html = False

    def action_close(self):
        """Close the wizard."""
        return {"type": "ir.actions.act_window_close"}
