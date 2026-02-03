# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResPartner(models.Model):
    _name = "res.partner"
    # mail.bounced.mixin must be inherited before res.partner to ensure its write()
    # method is executed first.
    # The native res.partner.write() stores incoming vals into pre_values_list for later
    # use by _fields_sync().
    # If mail.bounced.mixin is placed after res.partner, its write() will run after
    # res.partner.write(). In that case, the email_bounced field is not present in
    # pre_values_list, which causes an error when getting values in pre_values_list at
    # the line https://github.com/odoo/odoo/blob/97e90f14ea40e4dc8645f845ef78eb579bb3e8dc/odoo/addons/base/models/res_partner.py#L907
    # The inheritance order must be as below, or can be reverted after the Odoo PR
    # https://github.com/odoo/odoo/pull/246927 is merged.
    _inherit = ["mail.bounced.mixin", "res.partner"]

    # tracking_emails_count and email_score are non-store fields in order
    # to improve performance
    tracking_emails_count = fields.Integer(
        compute="_compute_email_score_and_count", readonly=True
    )
    email_score = fields.Float(compute="_compute_email_score_and_count", readonly=True)

    @api.depends("email")
    def _compute_email_score_and_count(self):
        self.email_score = 50.0
        self.tracking_emails_count = 0
        partners_mail = self.filtered("email")
        mt_obj = self.env["mail.tracking.email"].sudo()
        for partner in partners_mail:
            partner.email_score = mt_obj.email_score_from_email(partner.email)
            # We don't want performance issues due to heavy ACLs check for large
            # recordsets. Our option is to hide the number for regular users.
            if not self.env.user.has_group("base.group_system"):
                continue
            partner.tracking_emails_count = len(
                mt_obj._search([("recipient_address", "=", partner.email.lower())])
            )
