# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class FetchmailIncomingTestMixin(models.AbstractModel):
    _name = "fetchmail.incoming.test.mixin"
    _description = "Simulate an Incoming Email"

    def _default_server(self):
        """Preselect the server the wizard was opened from, none if several."""
        context = self.env.context
        if context.get("active_model") != "fetchmail.server":
            return False
        active_ids = context.get("active_ids") or []
        return active_ids[0] if len(active_ids) == 1 else False

    server_id = fields.Many2one(
        "fetchmail.server",
        string="Incoming Mail Server",
        default=lambda self: self._default_server(),
        help="Incoming mail server this wizard was opened from.",
    )

    def _build_raw_message(self):
        """Return the incoming email as raw bytes, as a mail server would."""
        raise NotImplementedError

    def action_process(self):
        """Feed the email to the mail gateway as a real inbound one."""
        self.ensure_one()
        fallback_model = self.server_id.object_id.model or None
        thread_id = self.env["mail.thread"].message_process(
            fallback_model, self._build_raw_message()
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("Email processed"),
                "message": _("The gateway created record #%s.", thread_id),
                "sticky": False,
                # Close the wizard dialog once the notification is shown.
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
