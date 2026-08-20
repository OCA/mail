This module extends mail_activity_restrict with team support.

For activity types with "Restrict Write to Assigned User" enabled, activity
team members are also allowed to edit and complete the activity.

No extra configuration field is added on the activity type. It reuses the
same restriction option from mail_activity_restrict and the team membership
from mail_activity_team.