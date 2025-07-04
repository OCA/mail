# Copyright 2025 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Mail Composer Direct Template",
    "summary": "The module allows to see and change directly email template",
    "version": "18.0.1.0.0",
    "development_status": "Production/Stable",
    "category": "Productivity/Discuss",
    "website": "https://github.com/OCA/mail",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "maintainers": ["trisdoan"],
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "preloadable": True,
    "depends": [
        "mail",
    ],
    "data": [
        "wizards/mail_compose_message_view.xml",
    ],
}
