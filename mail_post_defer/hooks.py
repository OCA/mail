# Copyright 2022-2023 Moduon Team S.L. <info@moduon.team>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Increase cadence of mail queue and notification crons."""
    crons = {
        "mail.ir_cron_mail_scheduler_action": "Mail: Email Queue Manager",
        "mail.ir_cron_send_scheduled_message": "Notification: Notify scheduled messages",  # noqa: E501
    }

    for cron_ref, description in crons.items():
        try:
            cron = env.ref(cron_ref)
        except ValueError:
            _logger.warning(
                "Couldn't find the %s cron (%s). "
                "Maybe no mails/notification will be ever sent!.",
                description,
                cron_ref,
            )
        else:
            _logger.info("Setting %s cron cadence to 1 minute", description)
            cron.interval_number = 1
            cron.interval_type = "minutes"
