# Copyright 2018-22 ForgeFlow <http://www.forgeflow.com>
# Copyright 2018 Odoo, S.A.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).


def _set_keep_done(cr):
    """Set keep_done to true for all existing activity types"""
    cr.execute(
        """
        update mail_activity_type
        set keep_done = true
        where keep_done is not true
        """
    )


def post_init_hook(env):
    _set_keep_done(env.cr)
