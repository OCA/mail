# Copyright 2026 Jarsa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Mail Attachment XML Preview",
    "summary": "Preview XML attachments as a collapsible tree instead of raw text",
    "version": "17.0.1.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/mail",
    "author": "Jarsa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["mail"],
    "assets": {
        "web.assets_backend": [
            "mail_attachment_xml_preview/static/src/attachment_model_patch.esm.js",
            "mail_attachment_xml_preview/static/src/xml_viewer.esm.js",
            "mail_attachment_xml_preview/static/src/xml_viewer.xml",
            "mail_attachment_xml_preview/static/src/xml_viewer.scss",
            "mail_attachment_xml_preview/static/src/file_viewer_patch.esm.js",
            "mail_attachment_xml_preview/static/src/file_viewer_patch.xml",
        ],
        "web.qunit_suite_tests": [
            "mail_attachment_xml_preview/static/tests/**/*.js",
        ],
    },
    "installable": True,
}
