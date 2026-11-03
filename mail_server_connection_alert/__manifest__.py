# Copyright 2026 CIT-Services
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Mail Server Connection Issue Alerts",
    "summary": "Incoming & Outgoing Mail Status Warning",
    "version": "18.0.1.0.0",
    "category": "Tools",
    "website": "https://github.com/OCA/mail",
    "author": "CIT-Services, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["base", "mail", "web_notify"],
    "data": [
        "data/test_connection.xml",
        "data/mail_alerts_channel.xml",
    ],
}
