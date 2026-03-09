To configure a forced layout for email templates:

1. Go to *Settings > Technical > Email > Email Templates*
2. Open the desired `email.template` record
3. In the *Settings* tab, find the *Force Layout* field

You can leave it empty to use the default email layout (chosen by Odoo).
You can force a custom email layout of your own. You can use the *Mail:
No-Layout notification template* to prevent Odoo from adding a layout.

To configure a custom layout of your own, some technical knowledge is
needed. You can see how the existing layouts are defined for details or
inspiration:

- `mail.mail_notification_layout`
- `mail.mail_notification_layout_with_responsible_signature`
- `mail.mail_notification_light`

To force a custom layout for emails that do not use an existing `email.template`
record (e.g., emails sent from the chatter), you can use the Layout Mapping feature:

1. Go to *Settings > Technical > User Interface > Views*
2. Copy the current layout (e.g., `mail.mail_notification_layout_with_responsible_signature`) to create a new custom layout, and customize it as needed
3. Open the original layout view that you want to replace. Under the *Layout Mapping* tab:
    * Click *Add a line*
    * Set *Substitute Layout* to the new custom layout you created
    * Set *Models* if you want to apply the replacement only to specific models. If left empty,
      the email layout will be replaced for all models
