import logging

from odoo.addons.mail.models.mail_activity import MailActivity

from .patch import mail_activity__create

_logger = logging.getLogger(__name__)


def post_load_hook():
    """See patch.py for more info"""
    MailActivity.create = mail_activity__create
    _logger.info("PATCHED mail's mail.activity create")
