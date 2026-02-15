from odoo import fields, models
from odoo.tools import config
from odoo.tools.safe_eval import safe_eval

from ..utils import _id_get


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    message_partner_ids = fields.Many2many(
        domain=lambda thread: thread.env[
            "mail.followers.edit"
        ]._mail_restrict_follower_selection_get_domain(thread._name)
    )

    def _message_get_suggested_recipients(
        self,
        reply_discussion=False,
        reply_message=None,
        no_create=True,
        primary_email=False,
        additional_partners=None,
    ):
        result = super()._message_get_suggested_recipients(
            reply_discussion=reply_discussion,
            reply_message=reply_message,
            no_create=no_create,
            primary_email=primary_email,
            additional_partners=additional_partners,
        )

        test_condition = config["test_enable"] and not self.env.context.get(
            "test_restrict_follower"
        )
        if test_condition or self.env.context.get("no_restrict_follower"):
            return result
        domain = self.env[
            "mail.followers.edit"
        ]._mail_restrict_follower_selection_get_domain()
        eval_domain = safe_eval(
            str(domain), context={"ref": lambda str_id: _id_get(self.env, str_id)}
        )
        items_to_remove = []
        for item in result:
            """ Removing partner_id to follow similar logic
                as of _message_add_suggested_recipient in version 18"""
            if not additional_partners:
                item.pop("partner_id")

            partner_id = item.get("partner_id", False)
            if partner_id:
                partner_count = self.env["res.partner"].search_count(
                    [("id", "=", partner_id)] + eval_domain
                )
                if not partner_count:
                    items_to_remove.append(item)
        for item in items_to_remove:
            result.remove(item)

        return result
