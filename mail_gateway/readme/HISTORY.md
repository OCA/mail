## 20.0.1.0.0

Migration to 20.0.

**Changes required by Odoo 20.0**

- The Discuss sidebar categories don't exist anymore: the gateway channels
  are listed in a new *Gateway* tab of the Discuss app and of the messaging
  menu, only shown to gateway users. As a consequence, the user setting
  *Gateway Category Open* has been removed.
- The `ir.websocket` override has been removed: Odoo already subscribes the
  users to the bus of the channels they are member of, gateway channels
  included.
- The `mail.resend.message` extension has been removed, as this wizard doesn't
  exist anymore. The failure reason of a gateway notification is now shown in
  the notification popover of the message.
- The pre-init hook has been removed: the column it created has not been used
  since 16.0.
