This module was written to allow you to restrict the selection of
possible followers. For example, if you use the social ERP functions
only internally, it makes sense to filter possible followers for being
employees. Otherwise, you'll get a quite crowded list of partners to
choose from.

The domain is enforced on every follower addition, not only in the
"Add Followers" wizard: partners subscribed programmatically (for example
the customer of a ticket or lead, the sender of an incoming email or the
recipients of a message) are silently skipped when they do not meet the
domain. The partner of the current user is always allowed, so users can
keep following the records they work on. Pass `no_restrict_follower` in
the context to bypass the restriction in custom code.
