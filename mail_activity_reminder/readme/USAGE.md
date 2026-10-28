Reminders are sent automatically by the *Mail Activity: Reminders* scheduled
action once a reminder offset of the activity type is reached.

The *Mail Activity: Reminder Report* scheduled action sends one report per user
listing:

- all overdue activities assigned to the user, oldest deadline first;
- all activities whose deadline lies within the reminder timeframe of their
  activity type, grouped by reminder level starting with the highest one.
  With reminders `5/2/0`, an activity due in 4 days is at reminder level 1
  and an activity due tomorrow is at reminder level 2.

Users without overdue or upcoming reminded activities receive no report. The
schedule of both actions can be adjusted under *Settings \> Technical \>
Scheduled Actions*.

In the activity list views, the *To Remind* filter shows the activities that
are not overdue but within the reminder timeframe of their activity type.
