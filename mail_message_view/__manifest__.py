{
    "name": "Mail Message View",
    "summary": "Browse chatter messages in a dedicated list view, "
    "separating user messages from system logs",
    "version": "16.0.1.0.0",
    "category": "Productivity/Discuss",
    "website": "https://github.com/OCA/mail",
    "author": "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["mail"],
    "data": [
        "data/ir_config_parameter.xml",
        "views/mail_message_views.xml",
    ],
    "installable": True,
}
