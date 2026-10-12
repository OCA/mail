1. Do the operation that posts the template automatically. With the example above,
   enable *Email Confirmation* in the Inventory settings and validate a delivery order.
2. A job *Post ... on ...* is created for each record. Once it is done, the email appears
   in the chatter of the record.

The option only applies to messages posted by the code with the template (the
`message_post_with_source` method). Emails sent by the user from the composer, and mass
mailings, are not affected.
