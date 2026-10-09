This Module adds the mail_attach_existing_attachment feature to the
account module, since there is a change in odoo 12.0, which adds a new
mail wizard form to the account module

The invoice's attachments are offered through the same foldable,
multi-column picker the mail composer uses, so a long-lived invoice does
not bury the wizard's own buttons under a column of checkboxes.
