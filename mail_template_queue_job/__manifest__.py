# Copyright 2026 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Template Queue Job",
    "summary": "Post the messages of selected email templates in a queue job",
    "version": "18.0.1.0.0",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "maintainers": ["sergio-teruel"],
    "website": "https://github.com/OCA/mail",
    "category": "Discuss",
    "license": "AGPL-3",
    "depends": ["mail", "queue_job"],
    "data": ["views/mail_template_views.xml"],
    "installable": True,
}
