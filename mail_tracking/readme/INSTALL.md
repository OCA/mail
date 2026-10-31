If you're using a multi-database installation (with or without dbfilter
option) where /web/databse/selector returns a list of more than one
database, then you need to add `mail_tracking` addon to wide load addons
list (by default, only `web` addon), setting `--load` option. For
example, `--load=web,mail,mail_tracking`

The first update of the module after this index was added creates a partial
index on `mail_message` (`mail_message_mail_tracking_needs_action_index`). Later
updates do not build it again: Odoo keeps it while its definition does not change.

On a database with a very large `mail_message` table that first build blocks
writes to the table while it runs (13 minutes on 122 million rows). To avoid the
lock, create the index beforehand exactly as the ORM would, with the comment it
stores on it; Odoo compares that comment with the index definition and keeps
the index when they match:

```sql
CREATE INDEX CONCURRENTLY mail_message_mail_tracking_needs_action_index
    ON mail_message (id) WHERE mail_tracking_needs_action IS TRUE;
COMMENT ON INDEX mail_message_mail_tracking_needs_action_index
    IS 'INDEX (id) WHERE mail_tracking_needs_action IS TRUE';
```
