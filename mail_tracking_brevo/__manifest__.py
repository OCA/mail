# Copyright 2026 CIT Services
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Mail tracking for Brevo",
    "summary": "Mail tracking and Brevo webhooks integration",
    "version": "18.0.1.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/mail",
    "author": "CIT-Services, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ["mail_tracking"],
    "data": [
        "views/res_partner.xml",
        "views/mail_tracking_email.xml",
        "wizards/res_config_settings_views.xml",
    ],
}
