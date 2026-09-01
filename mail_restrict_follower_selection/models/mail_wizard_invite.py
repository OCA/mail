# Copyright (C) 2015 Therp BV <http://therp.nl>
# Copyright (C) 2017 Komit <http://www.komit-consulting.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from lxml import etree

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval

from ..utils import _id_get


class MailWizardInvite(models.TransientModel):
    _inherit = "mail.wizard.invite"

    partner_ids_domain = fields.Binary(compute="_compute_partner_ids_domain")

    @api.depends("res_model")
    @api.depends_context("default_res_model")
    def _compute_partner_ids_domain(self):
        for wizard in self:
            domain = wizard._mail_restrict_follower_selection_get_domain(
                res_model=wizard.res_model
            )
            wizard.partner_ids_domain = safe_eval(
                str(domain),
                locals_dict={
                    "ref": lambda str_id, env=wizard.env: _id_get(env, str_id)
                },
            )

    @api.model
    def _mail_restrict_follower_selection_get_domain(self, res_model=None):
        if not res_model:
            res_model = self.env.context.get("default_res_model")
        parameter_name = "mail_restrict_follower_selection.domain"
        parameter_domain = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                f"{parameter_name}.{res_model}",
                self.env["ir.config_parameter"]
                .sudo()
                .get_param(parameter_name, default="[]"),
            )
        )
        domain = expression.AND(
            [safe_eval(parameter_domain), self._fields["partner_ids"].domain]
        )
        return domain

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type != "form":
            return result
        arch = etree.fromstring(result["arch"])
        partner_ids_fields = arch.xpath('//field[@name="partner_ids"]')
        if partner_ids_fields and not arch.xpath('//field[@name="partner_ids_domain"]'):
            domain_field = etree.Element("field")
            domain_field.attrib["name"] = "partner_ids_domain"
            domain_field.attrib["invisible"] = "1"
            partner_ids_fields[0].addprevious(domain_field)
        for field in partner_ids_fields:
            field.attrib["domain"] = "partner_ids_domain"
        result["arch"] = etree.tostring(arch)
        return result
