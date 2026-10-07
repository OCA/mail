# Copyright 2026 Quartile (https://quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Mail Message History",
    "summary": "Browse chatter messages in a dedicated list view, "
    "separating user messages from system logs",
    "version": "16.0.1.0.0",
    "category": "Productivity/Discuss",
    "website": "https://github.com/OCA/mail",
    "author": "Quartile, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["mail"],
    "data": [
        "data/ir_config_parameter.xml",
        "views/mail_message_views.xml",
    ],
    "maintainers": ["smorita7749"],
    "installable": True,
}
