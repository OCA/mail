To trigger the out-of-office notification:

1. An employee must have an approved leave covering today's date. This sets
   the employee's **Is Absent** field automatically.
2. The employee must be linked to an Odoo user.
3. Send any message that includes employee's partner in the recipients,
   for example, by mentioning them with `@name`.

When these conditions are met, the sender receives an internal note with the
expected return date of the absent employee, calculated as the first working
day after the leave ends based on the employee's working schedule and public
holidays.

The notification is sent at most once per user per day per employee. Sending
further messages to the same absent employee on the same day will not produce
additional notifications.
