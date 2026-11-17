Odoo sends one notification email per recipient partner. When several partners
notified by the same message share an email address, for example a company and
its delivery addresses following a transfer, that mailbox receives the same
email several times.

This module notifies only one partner per normalized email address. The other
partners with that address are left out of the notification, so the message
shows a single recipient for it. Internal users are kept before portal or
customer partners, and partners addressed explicitly by the message before
followers. Partners notified in the Odoo inbox are not affected.
