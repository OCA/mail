To use this module, follow these steps:

- Go to Settings > Technical > Email > Incoming Mail Servers.
- Open a saved server, or select one in the list.
- Click **Simulate Incoming Email** (button on the form, or the *Action* menu).
- Fill in the composer:
  - **To**: the alias that routes to your target model, e.g. a Helpdesk team alias.
  - **From**, **Cc**, **Bcc**, **Subject**, **Body** as needed.
- Click **Send**.

The message goes through the standard mail gateway and the created record (e.g. a
Helpdesk ticket) appears, just as if the email had been received.

To replay a real email instead of composing one:

- Click **Replay Email File** (button on the form, or the *Action* menu).
- Upload the message file, then click **Process**.

The file is sent to the gateway as if it was received through fetchmail.
Malformed HTML and unusual headers are preserved.

Both wizards reuse the **Create a New Record** model of the server they were
opened from, exactly like a real fetch: when the email replies to nothing and
matches no alias, the gateway creates a record of that model instead of
refusing the email.