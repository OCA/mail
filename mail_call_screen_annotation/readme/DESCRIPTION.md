This module lets the participants of a Discuss call draw on a shared screen,
in the spirit of the annotations of Google Meet, so they can point at what
they talk about: a field of a form, a line of a report, a button to click.

This first version draws vanishing ink: a stroke stays visible for two
seconds, then fades out. Each participant draws in their own color, and the
strokes of the other participants are labelled with their name.

The strokes are sent through the existing call connection (peer-to-peer or
SFU server). Nothing is stored on the server and no screen content is
changed: the ink is drawn over the video of the shared screen.
