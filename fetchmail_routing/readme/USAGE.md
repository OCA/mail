Additional incoming routes can be defined in the menu *Settings /
Technical / E-Mail / Incoming Routing* by defining small snippets which
yield a domain. This domain is used to select the record with the
correct thread to assign the mail to.

The following example code will try to extract the first invoice number from the
subject and assign the e-mail to the record.

```python
name = re.findall(r"(INV/\d{4}/\d{5,})", email["subject"])
if name:
    result = [("name", "=", name[0])]
```

*Allow manual assignment of mails* in the general configuration can be activated
to allow specific users with given rights to assign e-mails to existing threads or
create new threads out of mails which would be otherwise be ignored by Odoo itself.

The right *Assign E-Mails* can only view basic information like header, sender, and
recipients to assign the mail to a thread. The extended right *Manage E-Mails* can
also open the e-mail and read body and attachments.
