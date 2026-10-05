# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    def _action_send_mail(self, auto_commit=False):
        config = (
            self.env["mail.thread.disable.auto.followers.config"]
            .sudo()
            .search([], limit=1)
        )
        daf_models = config.model_ids.mapped("model") if config else []
        if (
            self.model in daf_models
            or self.env.context.get("active_model") in daf_models
        ):
            self = self.with_context(
                mail_create_nosubscribe=True,
                mail_post_autofollow=False,
                mail_thread_disable_auto_followers=daf_models,
            )
        return super()._action_send_mail(auto_commit=auto_commit)
