# Copyright 2025 Aulora AG
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
{
    "name": "Mail Reply Stop Notification",
    "summary": "Prevent notification emails to followers on a received reply",
    "version": "18.0.1.0.0",
    "category": "Mail",
    "website": "https://github.com/OCA/mail",
    "author": "Aulora AG, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["mail"],
    "development_status": "Production/Stable",
    "maintainers": ["realsaiko"],
    "data": [
        "views/res_config_settings.xml",
    ],
    "demo": ["demo/res_company_demo.xml"],
}
