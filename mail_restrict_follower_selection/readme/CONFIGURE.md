To configure this module, you need to go to System parameters and adjust
mail_restrict_follower_selection.domain as you see fit. This restricts
followers globally, if you want to restrict only the followers for a
certain record type (or have different restrictions for different record
types), create a parameter
mail_restrict_follower_selection.domain.\$your_model.

Some examples:

- `[("category_id.name", "=", "Employees")]` : Only allow contacts with 'Employees' tag
- `[("is_company", "=", False)]` : Restrict company contacts to be added as follower (to avoid emails to info@ email address)
- `[("user_ids","!=",False)]` : Restrict to contacts with user (internal and portal)
- `[("employee_ids","!=",False)]` : Restrict to employees

Note: This module won't change existing followers!
