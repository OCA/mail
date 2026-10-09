==========================================
Mail Activity Fetchmail With Team Activity
==========================================

Usage
-----

Uses mail.activity.team to configure automatic activities when mails arrive for the specified models.

The configuration to add RMA and PO models (Settings --> Technical --> Activity Teams menu).

Testing
-------

Team Creation:

1. Go to: "Settings" -> "Technical" -> "Activity" -> "Activity Teams"
2. Select or create a new team via the "+ New" button
3. Fill in the necessary details:

   - Name: e.g., ´Team1´
   - Team Leader: e.g., ´Person1´
   - Used models: e.g., ´Sales Order´ (can be more than one model assigned)
   - There has to be at least one "Member" per team ("Team Leader" is counted by default)

4. Press Save

Testing:

1. "Sales" -> "Orders" -> "Quotations" -> "+ New"
2. Fill in the necessary details
3. Send a message via the chat section in the SO
4. Check the recipients email inbox, you should have received an email
5. Reply to it
6. In Odoo you should see the message from the customer and a generated activity
