## For developers

By default, this module links activities to the `partner_id` field of the record.
If your model uses a different field to hold the related partner (e.g. `address_id`,
`contact_id`), you must override `_get_partner_field_name` to return that field name,
otherwise activity partner synchronization will have no effect on your model.

**When to override:**
- Your model inherits `mail.activity.mixin` but does not have a `partner_id` field.
- Your model has a partner relationship stored under a field with a name other than
  `partner_id`.

**Example:**

```python
class MyModel(models.Model):
    _name = "my.model"
    _inherit = ["mail.activity.mixin", "mail.thread"]

    address_id = fields.Many2one("res.partner")

    @api.model
    def _get_partner_field_name(self):
        return "address_id"
```

With this override, every time `address_id` is set or changed on a record, all linked
activities will automatically have their `partner_id` updated to match.

