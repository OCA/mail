# Copyright 2026 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Mail Recipient Blocklist",
    "summary": "Block outgoing emails by configurable recipient patterns",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/mail",
    "category": "Discuss",
    "depends": ["mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_recipient_block_rule_data.xml",
        "views/mail_recipient_block_rule_views.xml",
    ],
    "maintainers": ["sergio-teruel"],
    "application": False,
    "installable": True,
}
