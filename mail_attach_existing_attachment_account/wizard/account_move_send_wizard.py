# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMoveSendWizard(models.TransientModel):
    _inherit = "account.move.send.wizard"

    can_attach_attachment = fields.Boolean()
    object_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="account_move_send_wizard_ir_attachments_object_rel",
        column1="wizard_id",
        column2="attachment_id",
        string="Object Attachments",
    )
    display_object_attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        compute="_compute_display_object_attachment_ids",
    )

    @api.depends("move_id")
    def _compute_display_object_attachment_ids(self):
        for wizard in self:
            if self.move_id:
                attachments = self.env["ir.attachment"].search(
                    [
                        ("res_model", "=", "account.move"),
                        ("res_id", "=", self.move_id.id),
                    ]
                )
                wizard.display_object_attachment_ids = attachments
            else:
                wizard.display_object_attachment_ids = False

    @api.model
    def _get_invoice_extra_attachments(self, move):
        res = super()._get_invoice_extra_attachments(move)
        res |= self.object_attachment_ids
        return res

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if res.get("move_id") and not res.get("can_attach_attachment"):
            res["can_attach_attachment"] = True  # pragma: no cover
        return res
