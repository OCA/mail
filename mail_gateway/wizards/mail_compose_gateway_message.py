# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailComposeGatewayMessage(models.TransientModel):
    _name = "mail.compose.gateway.message"
    _inherit = "mail.compose.message"
    _description = "Mail Compose Gateway Message"

    wizard_partner_ids = fields.Many2many(
        "res.partner",
        "mail_compose_gateway_message_res_partner_rel",
        "wizard_id",
        "partner_id",
    )
    wizard_channel_ids = fields.Many2many(
        "res.partner.gateway.channel",
        "mail_compose_gateway_message_gateway_channel_rel",
        "wizard_id",
        "channel_id",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "mail_compose_gateway_message_ir_attachments_rel",
        "wizard_id",
        "attachment_id",
        "Attachments",
    )
    partner_ids = fields.Many2many(
        "res.partner",
        "mail_compose_gateway_message_res_partner_rel",
        "wizard_id",
        "partner_id",
        "Additional Contacts",
    )
    # Dummy compatibility with other OCA modules
    # OCA/mail_attach_existing_attachment
    object_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="mail_compose_gateway_message_ir_attachments_object_rel",
        column1="wizard_id",
        column2="attachment_id",
        string="Object Attachments",
    )
    # OCA/mail_composer_cc_bcc
    partner_cc_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="mail_compose_gateway_message_res_partner_cc_rel",
        column1="wizard_id",
        column2="partner_id",
        string="Cc",
    )
    partner_bcc_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="mail_compose_gateway_message_res_partner_bcc_rel",
        column1="wizard_id",
        column2="partner_id",
        string="Bcc",
    )

    @api.depends("wizard_partner_ids")
    def _compute_recipient_partners(self):
        # Messages are delivered through the selected gateway channels, so the
        # recipients are the gateway partners, never the ones suggested by a
        # mail template. partner_ids shares its relation with wizard_partner_ids.
        for composer in self:
            composer.partner_ids = composer.wizard_partner_ids
            composer.partner_cc_ids = False

    @api.depends("wizard_channel_ids")
    def _compute_partner_ids_all_have_email(self):
        # Gateway recipients do not need an email address
        self.partner_ids_all_have_email = True

    def _prepare_mail_values_dynamic(self, res_ids):
        self.ensure_one()
        values = super()._prepare_mail_values_dynamic(res_ids)
        values[res_ids[0]]["gateway_notifications"] = [
            {
                "partner_id": channel.partner_id.id,
                "channel_type": "gateway",
                "gateway_channel_id": channel.id,
            }
            for channel in self.wizard_channel_ids
        ]
        return values

    def _prepare_mail_values_static(self):
        values = super()._prepare_mail_values_static()
        values["gateway_notifications"] = [
            {
                "partner_id": channel.partner_id.id,
                "channel_type": "gateway",
                "gateway_channel_id": channel.id,
            }
            for channel in self.wizard_channel_ids
        ]
        return values
