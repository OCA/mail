This module introduces filter buttons in the chatter to separate user messages, notes, activities and tracked changes.
It adds a small toggle toolbar above the chatter that allows switching between:
- All messages: default view showing all messages
- Messages: only messages sent to or received from followers
- Notes: only internal notes
- Activities: planned activities and completed activities
- Changes: only tracked field changes

The buttons use the chatter message filters of Odoo, so the filtering is done on the server and covers all messages of the record.

Also, it keeps the chatter view selected when navigating between records/views, similar to how notebook tabs in form views remember the last selected tab.
