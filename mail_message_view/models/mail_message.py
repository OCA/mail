# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.tools.misc import format_date, format_datetime


class MailMessage(models.Model):
    _inherit = "mail.message"

    document_name = fields.Char(string="Document", compute="_compute_document_name")
    body_preview = fields.Char(compute="_compute_body_preview")
    tracking_summary = fields.Char(compute="_compute_tracking_summary")

    @api.depends("record_name", "model", "res_id")
    def _compute_document_name(self):
        # record_name is not stored for messages logged by the field tracking
        # (see mail.thread._message_log), so fall back on the document itself.
        messages_per_model = defaultdict(list)
        for message in self:
            if message.record_name:
                message.document_name = message.record_name
            elif message.model and message.res_id and message.model in self.env:
                messages_per_model[message.model].append(message)
            else:
                message.document_name = False
        for model_name, messages in messages_per_model.items():
            records = (
                self.env[model_name]
                .sudo()
                .with_context(active_test=False)
                .browse([message.res_id for message in messages])
                .exists()
            )
            # The document name is shown the same way as in the chatter, where
            # it is also read as sudo (see mail.message._message_format).
            names = {record.id: record.display_name for record in records}
            for message in messages:
                message.document_name = names.get(message.res_id, False)

    @api.depends("body")
    def _compute_body_preview(self):
        for message in self:
            message.body_preview = message._get_message_preview()

    @api.depends("tracking_value_ids")
    def _compute_tracking_summary(self):
        # tracking_value_ids is restricted to base.group_system, so it is read
        # as sudo and filtered on the field groups afterwards, the same way the
        # chatter does (see mail.message._message_format).
        for message, message_sudo in zip(self, self.sudo()):
            summary = []
            for tracking in message_sudo.tracking_value_ids:
                if (
                    tracking.field_groups
                    and not self.env.is_superuser()
                    and not self.user_has_groups(tracking.field_groups)
                ):
                    continue
                values = []
                for prefix in ("old", "new"):
                    value = tracking._get_display_value(prefix)[0]
                    if tracking.field_type == "boolean":
                        value = _("Yes") if value else _("No")
                    elif tracking.field_type in ("date", "datetime"):
                        # _get_display_value returns a raw UTC value, meant to be
                        # formatted client side.
                        raw = tracking[f"{prefix}_value_datetime"]
                        formatter = (
                            format_date
                            if tracking.field_type == "date"
                            else format_datetime
                        )
                        value = formatter(self.env, raw) if raw else ""
                    values.append("" if value is False or value is None else str(value))
                old_value, new_value = values
                summary.append(
                    "%s: %s → %s" % (tracking.field_desc, old_value, new_value)
                )
            message.tracking_summary = " | ".join(summary)
