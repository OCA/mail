# Copyright 2026 Quartile (https://quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import api, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.model_create_multi
    def create(self, values_list):
        self._fill_record_name(values_list)
        return super().create(values_list)

    @api.model
    def _fill_record_name(self, values_list):
        """Fill record_name on the messages logged by _message_log, which passes
        it as False, so that the logs show their document in the message history
        and can be searched and grouped by it.
        """
        todo = [
            values
            for values in values_list
            if "record_name" in values and not values["record_name"]
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
            names.update(
                {(model_name, record.id): record.display_name for record in records}
            )
        for values in todo:
            name = names.get((values["model"], values["res_id"]))
            if name:
                values["record_name"] = name
