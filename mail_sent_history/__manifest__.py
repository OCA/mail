# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Sent History",
    "summary": "View and browse messages and notes you have sent",
    "version": "17.0.1.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/mail",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["mail"],
    "assets": {
        "web.assets_backend": [
            "mail_sent_history/static/src/js/*",
            "mail_sent_history/static/src/xml/*",
        ],
    },
}
