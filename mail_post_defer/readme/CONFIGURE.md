You usually don't need to do anything. The module is configured appropriately out of the box.
Just make sure the following scheduled actions are active:

- Mail: Email Queue Manager (mail.ir_cron_mail_scheduler_action)
- Notification: Send scheduled message notifications (mail.ir_cron_send_scheduled_message)

The mail queue processing is made by a cron job. This is normal Odoo
behavior, not specific to this module. However, since you will start
using that queue for every message posted by any user in any thread,
this module configures that job to execute every minute by default.

You can still change that cadence after installing the module (although
it is not recommended). To do so:

1.  Log in with an administrator user.
2.  Activate developer mode.
3.  Go to *Settings \> Technical \> Automation \> Scheduled Actions*.
4.  Edit the action named "Mail: Email Queue Manager".
5.  Lower down the frequency in the field *Execute Every*. Recommended: 1 minute.