This module allows setting reminders for various Activity Types.

Two scheduled actions are provided:

- *Mail Activity: Reminders* runs hourly and notifies users about the
  activities assigned to them when a configured reminder offset is reached.
- *Mail Activity: Reminder Report* runs weekly and sends every user who has at
  least one overdue activity or one activity in the reminder timeframe a
  single report of those activities. The report is ordered by criticality:
  overdue activities first, followed by the activities grouped by reminder
  level, the highest level (closest to the deadline) first. The report does
  not count as a reminder and does not alter the regular reminder schedule.
