If you're using a multi-database installation (with or without dbfilter
option) where /web/databse/selector returns a list of more than one
database, then you need to add `mail_recipient_tracking` addon to wide load addons
list (by default, only `web` addon), setting `--load` option. For
example, `--load=web,mail,mail_recipient_tracking`

Since Odoo 20.0 the core provides a `mail_tracking` module (technical tracking
of field values), so this addon has been renamed to `mail_recipient_tracking`.
