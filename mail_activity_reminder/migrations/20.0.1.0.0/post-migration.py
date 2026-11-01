# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    view = env.ref(
        "mail_activity_reminder.message_activity_assigned", raise_if_not_found=False
    )
    if view and "<t t-esc=" in view.arch_db:
        view.arch_db = view.arch_db.replace("<t t-esc=", "<t t-out=")
