# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Notification Volume",
    "summary": "Allow users to configure notification sound volume",
    "version": "17.0.1.0.0",
    "development_status": "Beta",
    "category": "Social Network",
    "website": "https://github.com/OCA/mail",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["mail"],
    "data": [
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_notification_sound_volume/static/src/user_settings_service_patch.esm.js",
            "mail_notification_sound_volume/static/src/out_of_focus_service_patch.esm.js",
            "mail_notification_sound_volume/static/src/volume_slider_field.esm.js",
            "mail_notification_sound_volume/static/src/volume_slider_field.xml",
        ],
    },
}
