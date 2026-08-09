# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Mail User Signature Mass Edit Queued",
    "summary": "Queue mass user email signature updates generated from HTML templates.",
    "category": "Discuss",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "ACSONE SA/NV,Odoo Community Association (OCA)",
    "maintainers": ["sbejaoui"],
    "website": "https://github.com/OCA/mail",
    "depends": ["mail_user_signature_mass_edit", "queue_job"],
    "data": [
        "data/queue_job_channel.xml",
        "data/queue_job_function.xml",
        "views/signature_mass_edit_views.xml",
    ],
}
