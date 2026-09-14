# Copyright 2026 Quartile (https://quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.tools.misc import format_date, format_datetime


class MailMessage(models.Model):
    _inherit = "mail.message"

    tracking_summary = fields.Char(compute="_compute_tracking_summary")

    @api.model_create_multi
    def create(self, values_list):
        self._fill_record_name(values_list)
        return super().create(values_list)

    @api.model
    def _fill_record_name(self, values_list):
        """Store the document name on the messages core leaves it empty on.

        ``message_post`` lets ``create`` backfill ``record_name``, but
        ``_message_log`` and ``_message_log_batch`` pass it as ``False``, so the
        messages logged by the field tracking have no document name at all,
        which is what the message history is mostly made of.

        The user notifications are left alone on purpose: their empty document
        name drives the subject and the subtitle of their notification email
        (see ``mail.thread._notify_by_email_get_base_mail_values``).
        """
        todo = [
            values
            for values in values_list
            if "record_name" in values
            and not values["record_name"]
            and values.get("message_type") != "user_notification"
            and values.get("model")
            and values.get("res_id")
            and values["model"] in self.env
        ]
        if not todo:
            return
        res_ids_per_model = defaultdict(list)
        for values in todo:
            res_ids_per_model[values["model"]].append(values["res_id"])
        names = {}
        for model_name, res_ids in res_ids_per_model.items():
            records = (
                self.env[model_name]
                .sudo()
                .with_context(active_test=False)
                .browse(res_ids)
                .exists()
            )
            # The document name is read as sudo, the same way core does it (see
            # mail.message._get_record_name).
            names.update(
                {(model_name, record.id): record.display_name for record in records}
            )
        for values in todo:
            name = names.get((values["model"], values["res_id"]))
            if name:
                values["record_name"] = name

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
