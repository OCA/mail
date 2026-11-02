- Jobs only keep a few keys of the context (language, timezone, companies). The keys
  that decide when the email is sent (`force_send` and `mail_notify_force_send`) are
  carried to the job, but a template rendered from other context values would get them
  empty. Other modules can extend `_message_post_with_source_job_context_keys` to carry
  more keys.
- The code posting the template gets no message back, as it is created later by the job.
- Odoo already provides `sale_async_emails` to send the sales order confirmation email
  from a scheduled action. Use one or the other for that template.
