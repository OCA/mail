Define one email address per department on each company.

A new "Department Emails" tab on the company form lists, in an editable
list, the email address to use for each department (sales, purchase,
accounting, logistics, customer support). Addresses are validated on save.

The method `res.company.get_department_email(department)` returns the
address configured for a department on the company, or `False` if none is
set. Other modules can use it to pick the sender of outgoing emails.
