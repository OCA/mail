# Copyright 2024 Tecnativa - Carlos Lopez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Print Message",
    "version": "19.0.1.0.0",
    "summary": "Print messages from the chatter of any document. ",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/mail",
    "depends": ["mail", "contacts"],
    "data": [
        "data/report_paperformat_data.xml",
        "reports/report_mail_message.xml",
        "reports/reports.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_print/static/src/**/*.esm.js",
        ],
        "web.assets_tests": [
            "mail_print/static/tests/tours/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
