# Copyright 2018 David Juaneda - <djuaneda@sdi.es>
# Copyright 2021 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Activity Dashboard",
    "summary": "Add Activity Dashboards",
    "version": "18.0.1.0.0",
    "development_status": "Beta",
    "category": "Social Network",
    "website": "https://github.com/OCA/mail",
    "author": "SDi, David Juaneda, Sodexis, ACSONE SA/NV,"
    " Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["mail_activity_board", "spreadsheet_dashboard"],
    "data": ["security/groups.xml", "views/mail_activity_view.xml"],
}
