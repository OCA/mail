# Copyright 2026 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
{
    "name": "Mail Company Department",
    "summary": "Define one email address per department on each company",
    "version": "18.0.1.0.0",
    "category": "Discuss",
    "website": "https://github.com/OCA/mail",
    "author": "Camptocamp,Odoo Community Association (OCA)",
    "maintainers": ["simahawk"],
    "license": "LGPL-3",
    "installable": True,
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_company_views.xml",
    ],
}
