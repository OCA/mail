# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Mail User Signature Mass Edit",
    "summary": "Mass-edit user email signatures from an HTML template, "
    "rendered per user and filtered by company.",
    "category": "Mail",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "ACSONE SA/NV,Odoo Community Association (OCA)",
    "maintainers": ["sbejaoui"],
    "website": "https://github.com/OCA/mail",
    "depends": ["mail", "mass_mailing"],
    "data": [
        "security/res_groups.xml",
        "security/signature_mass_edit.xml",
        "views/signature_mass_edit_views.xml",
    ],
}
