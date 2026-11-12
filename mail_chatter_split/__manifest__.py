# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Chatter Split",
    "summary": "Separate user messages, notes, activities and changes in the chatter",
    "version": "20.0.1.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/mail",
    "author": "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["mail"],
    "assets": {
        "web.assets_backend": [
            "mail_chatter_split/static/src/chatter_patch.esm.js",
            "mail_chatter_split/static/src/search_message_input_patch.esm.js",
            "mail_chatter_split/static/src/chatter_patch.xml",
            "mail_chatter_split/static/src/chatter.scss",
        ],
        "web.assets_web_dark": [
            "mail_chatter_split/static/src/chatter.dark.scss",
        ],
    },
}
