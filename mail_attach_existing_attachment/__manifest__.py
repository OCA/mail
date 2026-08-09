# Copyright 2015 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Mail Attach Existing Attachment",
    "summary": "Adding attachment on the object by sending this one",
    "author": "ACSONE SA/NV, Tecnativa, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/mail",
    "category": "Social Network",
    "version": "19.0.2.0.0",
    "license": "AGPL-3",
    "depends": ["mail"],
    "data": ["wizard/mail_compose_message_view.xml"],
    "assets": {
        "web.assets_backend": [
            "mail_attach_existing_attachment/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "mail_attach_existing_attachment/static/tests/**/*",
        ],
    },
    "installable": True,
}
