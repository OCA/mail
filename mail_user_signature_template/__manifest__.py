# Copyright 2025 OCA Contributors
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "User Signature Template",
    "summary": "Company-wide signature templates for consistent email signatures",
    "version": "18.0.1.0.1",
    "development_status": "Beta",
    "category": "Social Network",
    "website": "https://github.com/OCA/mail",
    "author": "OCA Contributors, Odoo Community Association (OCA)",
    "maintainers": ["jwaes"],
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "mail",
        "base_setup",
        "utm",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/signature_template_views.xml",
        "views/res_company_views.xml",
        "views/res_users_views.xml",
        "wizard/signature_template_preview_views.xml",
        "wizard/signature_sanitization_check_views.xml",
        "data/utm_data.xml",
        "data/signature_template_data.xml",
        "data/server_actions.xml",
    ],
    "demo": [
        "demo/signature_template_demo.xml",
    ],
}
