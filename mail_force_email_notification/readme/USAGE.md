To use this module, you need to:

1. For developers implementing the feature:
   - Add the context key `force_notification_by_email=True` when sending messages through the mail thread
   ```python
   self.env['mail.thread'].with_context(
       force_notification_by_email=True
   ).message_post(
       body="Your message",
       partner_ids=[partner.id],
   )
   ```

2. For end users:
   - No specific configuration is needed
   - When developers have implemented the feature in specific actions:
     - Messages will be sent by email regardless of your notification preferences
     - You will receive email notifications even if you are connected to Odoo
     - Your notification preferences in your user settings won't affect these specific notifications

**Example Use Cases:**

- Critical notifications that need email documentation
- Automated workflows where email trail is required
- Compliance requirements where email proof of communication is necessary

**Note:** This module only affects notifications where the context key has been specifically implemented. All other notifications will follow standard Odoo behavior.