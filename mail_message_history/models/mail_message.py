# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import api, fields, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    model_description = fields.Char(
        string="Document Type",
        compute="_compute_model_description",
        search="_search_model_description",
    )

    @api.depends("model")
    def _compute_model_description(self):
        for message in self:
            message.model_description = (
                message.model and self.env["ir.model"]._get(message.model).name
            )

    def _search_model_description(self, operator, value):
        models = self.env["ir.model"].sudo().search([("name", operator, value)])
        return [("model", "in", models.mapped("model"))]

    @api.model_create_multi
    def create(self, values_list):
        self._fill_record_name(values_list)
        return super().create(values_list)

    @api.model
    def _get_record_names(self, model_name, res_ids):
        records = (
            self.env[model_name]
            .sudo()
            .with_context(active_test=False)
            .browse(res_ids)
            .exists()
        )
        return {record.id: record.display_name for record in records}

    @api.model
    def _fill_record_name(self, values_list):
        """Fill record_name on the messages logged by _message_log, which passes
        it as False, so that the logs can be searched by document.
        """
        todo = [
            values
            for values in values_list
            if "record_name" in values
            and not values["record_name"]
            and values.get("message_type") == "notification"
            and (values.get("body") or values.get("attachment_ids"))
            and values.get("model")
            and values.get("res_id")
        ]
        res_ids_per_model = defaultdict(list)
        for values in todo:
            res_ids_per_model[values["model"]].append(values["res_id"])
        names_per_model = {
            model_name: self._get_record_names(model_name, res_ids)
            for model_name, res_ids in res_ids_per_model.items()
        }
        for values in todo:
            name = names_per_model[values["model"]].get(values["res_id"])
            if name:
                values["record_name"] = name
