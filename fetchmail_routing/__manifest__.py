# © 2023 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Fetchmail - Extension of the Routing",
    "summary": "Control the assignment of incoming mails further",
    "version": "18.0.2.0.0",
    "category": "Hidden",
    "author": "initOS GmbH, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/mail",
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "mail",
    ],
    "data": [
        "security/security.xml",
        "data/actions.xml",
        "security/ir.model.access.csv",
        "views/fetchmail_routing_views.xml",
        "views/mail_unassigned_views.xml",
        "views/res_config_settings_views.xml",
        "wizards/mail_assign_wizard_views.xml",
    ],
}
