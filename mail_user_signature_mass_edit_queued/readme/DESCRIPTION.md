This module lets signature mass edit operations run through queue jobs.

A new *Run in Queue Job* option is added to signature mass edits.
When enabled, confirming a mass edit moves it to *In Progress*, creates one
queue job per matching user.
