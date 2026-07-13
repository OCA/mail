# Copyright - 2013-2026 Therp BV <https://therp.nl>.
# Copyright - 2026 Open Eye Development <https://openeyedev.eu>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Email gateway - folders",
    "summary": "Attach mails in an IMAP folder to existing objects",
    "version": "19.0.1.0.0",
    "author": "Therp BV,Open Eye Development,Odoo Community Association (OCA)",
    "maintainers": ["NL66278"],
    "website": "https://github.com/OCA/mail",
    "license": "AGPL-3",
    "category": "Tools",
    "depends": ["mail"],
    "data": [
        "views/fetchmail_server.xml",
        "wizard/attach_mail_manually.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "auto_install": False,
}
