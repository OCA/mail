# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Mail User Outgoing Server",
    "version": "18.0.1.0.0",
    "category": "Discuss",
    "summary": "Let each user connect their own Outlook mailbox as a personal "
    "outgoing mail server from their preferences",
    "license": "AGPL-3",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/mail",
    "development_status": "Beta",
    "maintainers": [],
    "depends": ["mail", "microsoft_outlook"],
    "data": [
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_user_outgoing_server/static/src/views/fields/"
            "mail_server_configurator_selection/"
            "mail_server_configurator_selection.esm.js",
            "mail_user_outgoing_server/static/src/views/fields/"
            "mail_server_configurator_selection/"
            "mail_server_configurator_selection.xml",
            "mail_user_outgoing_server/static/src/views/fields/"
            "mail_server_configurator_selection/"
            "mail_server_configurator_selection.scss",
        ],
    },
    "installable": True,
    "application": False,
}
