# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    use_autosubscribe_followers = fields.Boolean(default=True)

    def _generate_template_recipients(
        self,
        res_ids,
        render_fields,
        allow_suggested=False,
        find_or_create_partners=False,
        render_results=None,
    ):
        # Propagate the template-level "use_autosubscribe_followers" flag through
        # the context so that _message_get_default_recipients also respects it.
        if not self.use_autosubscribe_followers:
            self = self.with_context(no_autosubscribe_followers=True)
        res = super()._generate_template_recipients(
            res_ids,
            render_fields,
            allow_suggested=allow_suggested,
            find_or_create_partners=find_or_create_partners,
            render_results=render_results,
        )
        if self.env.context.get("no_autosubscribe_followers"):
            return res
        for res_id, values in res.items():
            partner_ids = values.get("partner_ids")
            if not partner_ids:
                continue
            partners = self.env["res.partner"].sudo().browse(partner_ids)
            ResModel = self.env[self.model]
            followers = ResModel._message_get_autosubscribe_followers(partners)
            follower_ids = [
                follower.id for follower in followers if follower not in partners
            ]
            res[res_id]["partner_ids"] += follower_ids
        return res
