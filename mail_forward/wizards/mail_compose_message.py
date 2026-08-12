# Copyright 2024 Tecnativa - Carlos Lopez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    forward_type = fields.Selection(
        [
            ("current_thread", "Current thread"),
            ("another_thread", "Another thread"),
        ],
        default="current_thread",
    )
    forward_thread = fields.Reference(
        selection="_selection_forward_thread", string="Thread to forward"
    )

    @api.model
    def _selection_forward_thread(self):
        # Get all models available to be selected by the user.
        # Only consider models that support posted messages and are not transient.
        models = (
            self.env["ir.model"]
            .sudo()
            .search(
                [
                    ("transient", "=", False),
                    ("is_mail_thread", "=", True),
                    ("enable_forward_to", "=", True),
                ],
                order="name asc",
            )
        )
        selection_values = []
        for model in models:
            if (
                model.model in self.env and self.env[model.model]._auto
            ):  # No Abstract models or reports
                selection_values.append((model.model, model.name))
        return selection_values

    def _action_send_mail(self, auto_commit=False):
        if self.forward_type == "another_thread" and self.forward_thread:
            # Add the body, subject, and partner_ids fields to write
            # to avoid setting them to False.
            # When template_id is not set,
            # these fields are set to False in the super() call.
            self.write(
                {
                    "model": self.forward_thread._name,
                    "res_ids": self.forward_thread.ids,
                    "body": self.body,
                    "subject": f"{self.env._('Fwd:')} {self.subject}",
                    "partner_ids": self.partner_ids,
                    "attachment_ids": self.attachment_ids,
                }
            )
        return super()._action_send_mail(auto_commit=auto_commit)
