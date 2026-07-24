Blocks outgoing emails addressed to recipients matching configurable block rules.
Rules can match exact emails, domains, contained text, wildcard patterns or regular expressions.
The block is enforced both on queued Odoo emails (`mail.mail`) and on direct SMTP deliveries (`ir.mail_server`).
