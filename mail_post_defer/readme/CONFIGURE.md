You usually don't need to do anything. The module is configured appropriately out of the box.
Just make sure the following scheduled actions are active:

- Mail: Email Queue Manager (mail.ir_cron_mail_scheduler_action)
- Notification: Notify scheduled messages (mail.ir_cron_send_scheduled_message)

The mail queue processing and scheduled messages notifications are handled by cron jobs.
This is normal Odoo behavior, not specific to this module. However, since you will start
using that queue for every message posted by any user in any thread,
both jobs are configured to execute every minute by default.

You can still change that cadence after installing the module (although
it is not recommended). To do so:

1.  Log in with an administrator user.
2.  Activate developer mode.
3.  Go to *Settings \> Technical \> Automation \> Scheduled Actions*.
4.  Find the cron(s) you want to adjust:
    - Mail: Email Queue Manager - handles outgoing emails.
    - Notification: Notify scheduled messages - handles notifications.
5.  Lower down the frequency in the field *Execute Every*. Recommended: 1 minute.
