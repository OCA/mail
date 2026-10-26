# Copyright 2026 Quartile (https://www.quartile.co)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Mail Max Email Size",
    "summary": "Send the attachments of large emails as download links",
    "version": "16.0.1.0.0",
    "category": "Productivity/Discuss",
    "website": "https://github.com/OCA/mail",
    "author": "Odoo SA, Quartile, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "depends": ["mail"],
    "data": [
        "data/ir_config_parameter_data.xml",
        "data/mail_templates.xml",
        "views/ir_mail_server_views.xml",
    ],
    "maintainers": ["smorita7749"],
    "installable": True,
}
