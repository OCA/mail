By default the standalone mentions of the brand that the Odoo templates
write as prose ("Welcome to Odoo", "Enjoy Odoo!", "A password reset was
requested for the Odoo account...") are replaced by the name of the
company, so the sentences still read well.

This can be changed with the `mail_debrand.brand_replacement` system
parameter (Settings \> Technical \> System Parameters):

- unset (default): the mentions are replaced by the company name.
- any other value: the mentions are replaced by that value.
- `False`: the mentions are left untouched and only the links to
  odoo.com are removed.

URLs, e-mail addresses and identifiers such as `odoo.com`,
`odoobot@example.com` or `OdooBot` are never modified.
