# Copyright 2026 Fasil
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Discuss Call Screen Annotation",
    "summary": "Draw vanishing ink on a screen shared in a Discuss call",
    "version": "20.0.1.0.0",
    "development_status": "Alpha",
    "category": "Productivity/Discuss",
    "website": "https://github.com/OCA/mail",
    "author": "Fasil,Odoo Community Association (OCA)",
    "maintainers": ["fasilwdr"],
    "license": "AGPL-3",
    "installable": True,
    "depends": ["mail"],
    "assets": {
        "web.assets_backend": [
            "mail_call_screen_annotation/static/src/**/*",
        ],
        "mail.assets_public": [
            "mail_call_screen_annotation/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "mail_call_screen_annotation/static/tests/**/*",
        ],
    },
}
