# Copyright 2016 La Louve
# Copyright 2019 Druidoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Email Template Conditional Attachment",
    "summary": "Allow to add conditional attachments to email templates",
    "version": "12.0.1.0.0",
    "category": "Uncategorized",
    "website": "https://github.com/druidoo/druidoo-addons",
    "author": "La Louve, Druidoo, Odoo Community Association (OCA)",
    "maintainers": [
        "ivantodorovich"
    ],
    "license": "AGPL-3",
    "depends": [
        "mail",
    ],
    "data": [
        "views/mail_template.xml",
        "security/ir.model.access.csv",
    ],
    "demo": [
        "demo/mail_template.xml",
    ],
}
