## 20.0.1.0.0

Migration to 20.0.

- The web client code has been rewritten: the former patches used the legacy
  messaging models, which don't exist anymore. Now the module only registers
  the Telegram icon of the gateway, used in the *Gateway* tab of the Discuss
  app and in the notifications of the messages.
- Incoming messages from people not linked to a contact are now posted with
  their guest as author, instead of the webhook user.
- The delivery status of sent messages is refreshed with the standard
  notification update of the message.
