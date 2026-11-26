# Copyright 2026 Reinaldo J. Menendez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Mail Activity Reassign on Archive",
    "summary": "Reassign activities instead of deleting when users are archived",
    "version": "18.0.1.0.0",
    "category": "Discuss",
    "website": "https://github.com/OCA/mail",
    "author": "Reinaldo J. Menendez, Odoo Community Association (OCA)",
    "maintainers": ["rejamen"],
    "license": "AGPL-3",
    "installable": True,
    "depends": ["mail"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
}
