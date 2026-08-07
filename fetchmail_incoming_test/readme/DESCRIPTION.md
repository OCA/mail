This module lets you simulate an incoming email directly from Odoo,
without a real mail server or SMTP client.

It adds a **Simulate Incoming Email** button (and matching *Action* menu entry) on
the Incoming Mail Server, opening a small composer (From, To, Cc, Bcc, Subject, Body).
On send, the email is used as if it had been fetched from a server,
it is then routed by alias and creates the target record
(helpdesk ticket, lead, task, ...).

It is meant for testing mail-driven flows on environments that have no inbound mail server,
like test instances.

It also adds a **Replay Email File** button, which takes a raw message file
(usually a `.eml` exported from a mail client) and feeds it to the gateway
untouched. Useful to reproduce how a specific email that a customer received
was handled, byte for byte.
