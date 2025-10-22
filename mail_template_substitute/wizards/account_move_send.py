# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMoveSend(models.TransientModel):
    _inherit = "account.move.send.wizard"

    def _compute_mail_template_id(self):
        res = super()._compute_mail_template_id()
        for wizard in self:
            template = wizard._get_substitution_template(
                wizard.mail_template_id, wizard.move_id.ids
            )
            if template:
                wizard.mail_template_id = template
        return res

    @api.model
    def _get_substitution_template(self, template, res_ids):
        if template:
            res_ids_to_templates = template._classify_per_lang(res_ids)
            if len(res_ids_to_templates):
                _lang, (template, _res_ids) = list(res_ids_to_templates.items())[0]
                return template
        return False
