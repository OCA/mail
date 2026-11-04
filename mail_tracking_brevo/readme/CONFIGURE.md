To configure this module, you need to:

1.  Go to [Brevo](https://developers.brevo.com), create an account and validate your sending [domain](https://app.brevo.com/senders/domain/list).
2.  Create [API](https://app.brevo.com/settings/keys/api) key and the [SMTP](https://app.brevo.com/settings/keys/smtp)
3.  Go back to Odoo.
4.  Go to *Settings \> General Settings \> Emails \> Enable mail
    tracking with Brevo*.
5.  Fill all the values.
6.  Optionally click *Unregister Brevo webhooks* and accept.
7.  Click *Register Brevo webhooks*.

You can also config timeout for brevo with this system parameter:

- `brevo.timeout`: Set it to a number of seconds.
