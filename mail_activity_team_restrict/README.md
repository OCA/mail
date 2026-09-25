# Mail Activity Team Restrict

This module extends `mail_activity_restrict` together with `mail_activity_team`.

When `can_write_restrict` is enabled on an activity type, the base module limits edits
to the assigned user. This addon extends that rule so members of the activity `team_id`
may also edit the activity and mark it as done.

No additional configuration is introduced. The module reuses:

- `mail.activity.type.can_write_restrict` from `mail_activity_restrict`
- `mail.activity.team_id` and `mail.activity.team.member_ids` from `mail_activity_team`
