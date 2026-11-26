Some emails are posted automatically while the user is doing something else: the
delivery confirmation when a transfer is validated, the confirmation of a sales order,
a rating request... Rendering the reports attached to those emails can take a few
seconds, and the user has to wait for it before the operation finishes.

This module adds an option to email templates to post those messages in a queue job
instead, so the operation does not wait for the email. Only the message of the template
is delayed: everything else done by the operation still runs as usual.
