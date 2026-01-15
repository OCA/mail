# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Activity Future Counter",
    "summary": """Add a badge counter on the bottom-right of the activity
    clock icon of the navigation bar, showing the count of future activities.""",
    "version": "17.0.1.0.0",
    "development_status": "Beta",
    "category": "Social Network",
    "website": "https://github.com/OCA/mail",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["mail"],
    "assets": {
        "web.assets_backend": [
            "mail_activity_future_counter/static/src/activity_menu_patch.esm.js",
            "mail_activity_future_counter/static/src/activity_menu_patch.xml",
            "mail_activity_future_counter/static/src/activity_menu_patch.scss",
        ],
    },
}
