# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models


class MailActivityMixin(models.AbstractModel):
    _inherit = "mail.activity.mixin"

    @api.model_create_multi
    def create(self, vals_list):
        record_ids = super().create(vals_list)
        for rec, vals in zip(record_ids, vals_list, strict=True):
            if rec and self._activity_partner_need_update(vals):
                rec._update_activity_partner()
        return record_ids

    def write(self, vals):
        res = super().write(vals)
        if res and self._activity_partner_need_update(vals):
            self._update_activity_partner()
        return res

    @api.model
    def _get_partner_field_name(self):
        """Return the name of the partner field to link activities to.
        By default, it's `partner_id`, but it can be overridden by models that
        want to link activities to a different partner field."""
        return "partner_id"

    @api.model
    def _activity_partner_need_update(self, vals):
        res = False
        partner_field_name = self._get_partner_field_name()
        if partner_field_name in self._fields:
            # Use set intersection to find out if the `partner_id` of
            # linked activities must be updated
            depends_fields = [partner_field_name]
            if depends_fields and (set(vals) & set(depends_fields)):
                res = True
        return res

    def _update_activity_partner(self):
        for rec in self:
            partner_field_name = rec._get_partner_field_name()
            partner_id = rec[partner_field_name]
            rec.activity_ids.write({"partner_id": partner_id.id})
