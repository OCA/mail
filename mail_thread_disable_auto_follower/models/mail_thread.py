# Copyright 2026 CIT Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model_create_multi
    def create(self, vals_list):
        config = (
            self.env["mail.thread.disable.auto.followers.config"]
            .sudo()
            .search([], limit=1)
        )
        daf_models = config.model_ids.mapped("model") if config else []
        if (
            not self.env.context.get("mail_thread_allow_auto_followers")
            and self._name in daf_models
        ):
            self = self.with_context(
                mail_create_nosubscribe=True,
                mail_thread_disable_auto_followers=daf_models,
                active_model=self._name,
            )
        return super().create(vals_list)

    def write(self, vals):
        config = (
            self.env["mail.thread.disable.auto.followers.config"]
            .sudo()
            .search([], limit=1)
        )
        daf_models = config.model_ids.mapped("model") if config else []
        if (
            not self.env.context.get("mail_thread_allow_auto_followers")
            and self._name in daf_models
        ):
            self = self.with_context(mail_thread_disable_auto_followers=daf_models)
        return super().write(vals)

    @api.returns("mail.message", lambda value: value.id)
    def message_post(self, **kwargs):
        """
        We also need to handle the case where the create/write context
        is gone (e.g. mail wizard).
        """
        if not self.env.context.get(
            "mail_thread_allow_auto_followers"
        ) and self.env.context.get("mail_post_autofollow"):
            config = (
                self.env["mail.thread.disable.auto.followers.config"]
                .sudo()
                .search([], limit=1)
            )
            daf_models = config.model_ids.mapped("model") if config else []
            if self._name in daf_models:
                self = self.with_context(
                    mail_post_autofollow=False,
                    mail_create_nosubscribe=True,
                )
        return super().message_post(**kwargs)

    def message_subscribe(self, partner_ids=None, subtype_ids=None):
        """
        In some cases message_subscribe is called explicitly.
        """
        daf_models = self.env.context.get("mail_thread_disable_auto_followers", [])
        if (
            not self.env.context.get("mail_thread_allow_auto_followers")
            and daf_models
            and self._name in daf_models
        ):
            partner_ids = None
        return super().message_subscribe(
            partner_ids=partner_ids, subtype_ids=subtype_ids
        )

    def _message_auto_subscribe_followers(self, updated_values, default_subtype_ids):
        daf_models = self.env.context.get("mail_thread_disable_auto_followers", [])
        if (
            not self.env.context.get("mail_thread_allow_auto_followers")
            and self._name in daf_models
        ):
            return []
        return super()._message_auto_subscribe_followers(
            updated_values, default_subtype_ids
        )
