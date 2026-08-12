This module adds a *Discuss > Message History* menu listing the chatter messages
(``mail.message``) of all the documents, to search them and group them, e.g. by
model. Only the messages the user is allowed to see are listed.

The list tells the messages posted by users apart from the ones logged by the
system, and shows as plain text the message body and the tracked field changes,
e.g. ``Status: RFQ → Purchase Order``. A filter narrows the list to the messages
that have an attachment, and opening a message shows its attachments.

A smart button on the form views opens the same list for a single record.

Odoo leaves the document name empty on the messages it logs, so the *Document*
column would be empty on most of the history. The module therefore fills the
field when such a message is created, which also makes the column searchable,
sortable and groupable. The user notifications are left untouched, as their empty
document name drives the subject of their notification email.
