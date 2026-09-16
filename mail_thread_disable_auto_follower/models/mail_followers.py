# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MailFollowers(models.AbstractModel):
    _inherit = "mail.followers"

    def _get_subscription_data(
        self, doc_data, pids, include_pshare=False, include_active=False
    ):
        res = super()._get_subscription_data(
            doc_data, pids, include_pshare=include_pshare, include_active=include_active
        )
        daf_models = self.env.context.get("mail_thread_disable_auto_followers", [])
        if (
            self.env.context.get("mail_create_nosubscribe")
            and self.env.context.get("active_model") in daf_models
        ):
            res_out = []
            for row in res:
                row_list = list(row)
                row_list[2] = None  # Replace partner_id (index 2) with None
                res_out.append(tuple(row_list))
            return res_out
        return res
