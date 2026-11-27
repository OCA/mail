This module was written to allow you to restrict the selection of
possible followers. For example, if you use the social ERP functions
only internally, it makes sense to filter possible followers for being
employees. Otherwise, you'll get a quite crowded list of partners to
choose from.

The domain is enforced on every follower addition, not only in the
"Add Followers" wizard: partners subscribed programmatically (for example
the sender of an incoming email, the recipients of a message) or 
automatically (for example the assignee of a task or the salesperson of 
an order) are silently skipped when they do not meet the domain.

The domain applies to every partner, including the current user: a user
that does not meet the domain is not subscribed when creating a record,
when being assigned, nor when posting a message, and gets an error when
clicking the "Follow" button.

Exceptions:

- Existing followers are never changed, and their subscription (subtypes)
  can still be edited.
- Pass `no_restrict_follower` in the context to bypass the restriction in
  custom code.
