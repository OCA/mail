- This module is a **backport**. The per-user outgoing mail server feature is
  available **natively from Odoo 19.0** (in the `mail` / `microsoft_outlook`
  core modules). Therefore this module is meant for **18.0 only** and should
  **not** be migrated to 19.0 or later — on those versions the functionality is
  already provided by Odoo.
- Only **Outlook** is supported. Gmail OAuth (covered natively in 19.0 too) is
  out of scope here.
- Compared to the 19.0 implementation, the following refinements are
  intentionally **not** backported, as they are not required for the feature to
  work on 18.0:
  - the per-author candidate-set routing in `mail.mail` (on 18.0 outgoing mail
    is already routed by the exact `from_filter` match in
    `ir.mail_server._find_mail_server`);
  - the per-minute anti-spam throttling of personal mail servers;
  - the post-OAuth check that the Microsoft login email matches the server
    email (18.0's OAuth scope does not return an `id_token`; the server's
    `from_filter` is still locked to the user's address and Microsoft enforces
    send-as on its side).
