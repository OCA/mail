Odoo notification emails sent to non-internal recipients can include an
access button, granting access to the Odoo instance and the related
document without logging in.

This module restricts that access button so it is only shown to
recipients who have a user account (internal users or portal users) and
never to unregistered external partners. These external recipients will
still receive the email, but the button will be removed.

This logic applies dynamically across all recipient groups, including
mixed ones (portal_customer) that contain both types of contacts.

A registered recipient in a mixed group keeps the button (and the
group), while an unregistered one in that same context is automatically
moved to the next buttonless group or the fallback group (buttonless
too).
