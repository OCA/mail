# Copyright 2026 Jarsa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Mail Attachment Office Preview",
    "summary": "Preview Office attachments in the browser "
    "by converting them to PDF with LibreOffice",
    "version": "17.0.1.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/mail",
    "author": "Jarsa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["mail"],
    "external_dependencies": {"deb": ["libreoffice"]},
    "assets": {
        "web.assets_backend": [
            "mail_attachment_office_preview/static/src/attachment_model_patch.esm.js",
            "mail_attachment_office_preview/static/src/file_viewer_patch.esm.js",
            "mail_attachment_office_preview/static/src/file_viewer_patch.xml",
        ],
    },
    "installable": True,
}
