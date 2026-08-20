This module lets **each user connect their own Outlook mailbox** as a personal
outgoing mail server, directly from their own preferences, without an
administrator having to do it on their behalf.

In stock Odoo 18 the Outlook OAuth flow (opening the Microsoft login and the
OAuth callback) is restricted to `base.group_system` users, so a regular user
cannot authenticate their own mailbox. This module:

- Adds an **Outgoing Mail Server** selector on *My Preferences*
  (`Default` / `Outlook`). Picking `Outlook` creates the user's personal
  outgoing mail server and starts the OAuth flow in the user's own session.
- Adds `owner_user_id` on `ir.mail_server` to tie a personal server to a single
  user, and keeps those personal servers out of the generic / fallback server
  selection, so a personal mailbox is only ever used to send its owner's own
  email (matched by the `From` address).
- Lets the **owner** of a personal server (a non-admin user) run the Outlook
  OAuth flow and complete the callback, activating the server once the login
  succeeds.

> **Note:** this is a backport. The feature is available **natively from Odoo
> 19.0**, so this module only makes sense on 18.0. See the *Roadmap* section.
