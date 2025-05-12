import logging

from odoo.addons.mail_activity_done.hooks import _set_keep_done


def migrate(cr, version):
    """Deal with possible inconsistencies between active and done.

    Set done activities that were not archived to archived.
    Warn about possible archived activities that were not done.
    """
    logger = logging.getLogger("odoo.addons.mail_activity_done.migrations")
    _set_keep_done(cr)
    cr.execute(
        "update mail_activity set active = false where active and done;",
    )
    if cr.rowcount:
        logger.info(
            f"{cr.rowcount} done activities were previously unarchived. They are "
            "now set back to archived for Odoo to still consider them done.",
        )
    cr.execute(
        "select id from mail_activity where active is not true and done is not true;",
    )
    ids = [str(row[0]) for row in cr.fetchall()]
    if ids:
        logger.warning(
            f"{len(ids)} activities were previously archived but not "
            "done. Odoo will consider them done now (activities with ids "
            f"{','.join(ids)})"
        )
