# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Disable Mail Thread Auto-follower",
    "summary": "Disable automatic follower subscriptions on selected models.",
    "author": "CIT Services, Odoo Community Association (OCA)",
    "company": "CIT Services",
    "website": "https://github.com/OCA/mail",
    "category": "Social Network",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "depends": ["mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_thread_disable_auto_followers_data.xml",
        "views/mail_thread_disable_auto_followers_views.xml",
    ],
    "installable": True,
}
