# Copyright (C) 2015 Therp BV <http://therp.nl>
# Copyright (C) 2017 Komit <http://www.komit-consulting.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from lxml import etree

from odoo import api, models
from odoo.fields import Command, Domain
from odoo.tools.safe_eval import safe_eval

from ..utils import _id_get


class MailFollowersEdit(models.TransientModel):
    _inherit = "mail.followers.edit"

    @api.model
    def _mail_restrict_follower_selection_get_domain(self, res_model=None):
        if not res_model:
            res_model = self.env.context.get("default_res_model")
        parameter_name = "mail_restrict_follower_selection.domain"
        IrConfigParameter = self.env["ir.config_parameter"].sudo()
        parameter_domain = IrConfigParameter.get_param(
            f"{parameter_name}.{res_model}",
            IrConfigParameter.get_param(parameter_name, default="[]"),
        )
        domain = Domain.AND(
            [
                safe_eval(
                    parameter_domain, {"ref": lambda str_id: _id_get(self.env, str_id)}
                ),
                self._fields["partner_ids"].domain,
            ]
        )
        return domain

    def edit_followers(self):
        if not self.env.context.get("no_restrict_follower"):
            for wizard in self.filtered(lambda w: w.operation == "add"):
                domain_str = str(
                    self._mail_restrict_follower_selection_get_domain(
                        res_model=wizard.res_model
                    )
                )
                allowed_partners = self.env["res.partner"].search(
                    [("id", "in", wizard.partner_ids.ids)]
                    + safe_eval(
                        domain_str,
                        {"ref": lambda str_id: _id_get(self.env, str_id)},
                    )
                )
                wizard.write({"partner_ids": [Command.set(allowed_partners.ids)]})
        return super().edit_followers()

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)

        # `restrict_follower_res_model_view_ref` is set by the
        # FollowerList JS patch; it is the only way to forward the
        # followed record's model to `get_view`, since the web client
        # strips all context keys except `lang` and `*_view_ref`
        # before calling `get_views`. `default_res_model` is kept as a
        # fallback for callers reached without the JS patch, e.g.
        # act_window bindings like helpdesk's `Add/remove followers`.
        res_model = self.env.context.get("restrict_follower_res_model_view_ref")
        arch = etree.fromstring(result["arch"])
        domain = self._mail_restrict_follower_selection_get_domain(res_model=res_model)
        eval_domain = safe_eval(
            str(domain), {"ref": lambda str_id: _id_get(self.env, str_id)}
        )
        for field in arch.xpath('//field[@name="partner_ids"]'):
            field.attrib["domain"] = str(eval_domain)
        result["arch"] = etree.tostring(arch, encoding="unicode")
        return result
