This module was written to allow you to restrict the selection of
possible followers. For example, if you use the social ERP functions
only internally, it makes sense to filter possible followers for being
employees. Otherwise, you'll get a quite crowded list of partners to
choose from.

The restriction is applied to the **Add Followers** wizard: only
contacts matching the configured domain can be selected, and any contact
that does not match it is discarded when the wizard is confirmed.

The restriction does not apply to followers added automatically by Odoo
or by other modules (for example, the customer subscribed when a message
is posted, or followers added from code), nor to the recipients
suggested by the chatter composer.
