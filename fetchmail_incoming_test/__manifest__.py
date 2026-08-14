# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Fetchmail Incoming Test",
    "version": "18.0.1.1.0",
    "category": "Discuss",
    "website": "https://github.com/OCA/mail",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "summary": "Simulate an incoming email from the Incoming Mail Server form",
    "depends": ["mail"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/fetchmail_incoming_test_views.xml",
        "wizards/fetchmail_incoming_test_eml_views.xml",
        "views/fetchmail_server_views.xml",
    ],
    "installable": True,
}
