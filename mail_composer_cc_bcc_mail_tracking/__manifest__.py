# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Email CC and BCC - Mail Tracking",
    "summary": "Show Cc/Bcc recipients below the To line in the chatter.",
    "version": "18.0.1.0.0",
    "development_status": "Alpha",
    "category": "Social",
    "website": "https://github.com/OCA/mail",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "auto_install": True,
    "depends": [
        "mail_composer_cc_bcc",
        "mail_tracking",
    ],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_composer_cc_bcc_mail_tracking/static/src/message_model.esm.js",
            "mail_composer_cc_bcc_mail_tracking/static/src/message.esm.js",
            "mail_composer_cc_bcc_mail_tracking/static/src/message.xml",
        ],
    },
}
