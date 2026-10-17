# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Mail suggested recipient unchecked",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/mail",
    "version": "19.0.1.0.0",
    "depends": ["mail"],
    "license": "AGPL-3",
    "category": "Tools",
    "installable": True,
    "maintainers": ["victoralmau"],
    "assets": {
        "web.assets_backend": [
            "mail_suggested_recipient_unchecked/static/src/**/*",
        ],
        "web.assets_tests": [
            "mail_suggested_recipient_unchecked/static/tests/tours/**/*",
        ],
    },
}
