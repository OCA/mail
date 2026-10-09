# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mail Activity on Fetchmail with Team Activity",
    "version": "18.0.1.0.0",
    "category": "Social Network",
    "author": "Nitrokey GmbH, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/mail",
    "license": "AGPL-3",
    "summary": """
    * Uses mail.activity.team to configure automatic activities when mails
     arrive for the specified models.
    * The configuration to add RMA and PO models
     (Settings --> Technical --> Activity Teams menu)
     """,
    "depends": ["mail_activity_team", "calendar"],
    "installable": True,
}
