Glue module between
- [mail_composer_cc_bcc](../mail_composer_cc_bcc)
- [mail_tracking](../mail_tracking).

It shows, in the chatter, which recipients were in To, Cc and Bcc for each
sent message, reusing mail_tracking's clickable recipient widget.

## Features

- The "To" line rendered by mail_tracking becomes collapsible:
  - shows all recipients
  - expanding it splits them into To / Cc / Bcc
- Global setting to choose which one is the default (collapsed or expanded)
- Global setting to choose whether or not we can collapse from one mode to the other
