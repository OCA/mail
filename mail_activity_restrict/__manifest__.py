{
    "name": "Mail Activity Write Restriction",
    "version": "19.0.1.0.0",
    "category": "Productivity/Mail",
    "license": "AGPL-3",
    "author": "glueckkanja AG, Odoo Community Association (OCA)",
    "summary": "Restrict write access to mail activities based on assigned user",
    "maintainers": ["CRogos"],
    "website": "https://github.com/OCA/mail",
    "depends": [
        "mail",
    ],
    "data": [
        "views/mail_activity_type_views.xml",
    ],
    "installable": True,
    "application": False,
}
