To configure department emails:

1. Go to Settings > Companies and open the company.
2. Open the "Department Emails" tab.
3. Add one line per department, select the department and enter its email.

From code:

.. code-block:: python

    email_from = self.env.company.get_department_email("sale")
