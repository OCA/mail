When Odoo receives a mail on a record, it forwards a copy to every follower of
the record, sent as `<sender name> <catchall address>`.

This copy:

- leaks replies meant for the company only to the other external followers;
- is flagged as impersonation by some mail servers (e.g. Microsoft Defender).

This module stops forwarding incoming mails to the followers by email.
The mail is still logged in the chatter, and followers notified in their Odoo
inbox are still notified.
