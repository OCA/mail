# © 2024 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import email
import logging
from datetime import datetime, timedelta
from email.message import EmailMessage

from odoo import _, api, fields, models
from odoo.tools.mail import email_split_tuples

_logger = logging.getLogger(__name__)


class MailUnassigned(models.Model):
    _name = "mail.unassigned"
    _description = "Unassigned E-Mails"
    _rec_name = "subject"
    _order = "create_date DESC"

    def _get_thread_models(self):
        models = (
            self.env["ir.model.fields"]
            .sudo()
            .search([("name", "=", "message_partner_ids")])
            .mapped("model_id")
        )
        return sorted(
            [
                (m.model, m.name)
                for m in models
                if m.model in self.env and self.env[m.model]._auto
            ],
            key=lambda x: x[1],
        )

    email_from = fields.Char(string="From", readonly=True)
    email_to_ids = fields.One2many(
        "mail.unassigned.receiver",
        "mail_id",
        string="To",
        domain=[("type", "=", "to")],
        readonly=True,
    )
    email_cc_ids = fields.One2many(
        "mail.unassigned.receiver",
        "mail_id",
        string="CC",
        domain=[("type", "=", "cc")],
        readonly=True,
    )
    message_id = fields.Char("Message ID", readonly=True)
    subject = fields.Char(readonly=True)
    fetchmail_server_id = fields.Many2one(
        "fetchmail.server",
        string="Incoming Mail Server",
        readonly=True,
    )
    body = fields.Html(readonly=True, groups="fetchmail_routing.group_mail_manager")
    message = fields.Text(readonly=True, groups="base.group_system")
    thread_id = fields.Reference("_get_thread_models", readonly=True)
    model = fields.Selection("_get_thread_models", readonly=True)
    color = fields.Integer("Marker", help="Used for manual highlighting")
    has_attachments = fields.Boolean(
        compute="_compute_has_attachment", compute_sudo=True
    )
    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Attachments",
        groups="fetchmail_routing.group_mail_manager",
        readonly=True,
    )

    @api.depends("attachment_ids")
    def _compute_has_attachment(self):
        for rec in self:
            rec.has_attachments = bool(rec.attachment_ids)

    @api.autovacuum
    def _gc_remove_old_unassigned_mails(self):
        days = self.env.company.delete_unassigned_after
        if days:
            threshold = datetime.utcnow() - timedelta(days=days)
            domain = [("create_date", "<", threshold)]
            return self.sudo().search(domain).unlink()

    @api.model
    def process_from_email(self, mail):
        if isinstance(mail, str):
            mail = mail.encode()

        message = email.message_from_bytes(mail, policy=email.policy.SMTP)
        msg_dict = self.env["mail.thread"].message_parse(message)
        self.process_unassigned(mail.decode(), msg_dict)

    def _required_message_dict_fields(self):
        return {"email_from", "message_id", "subject", "body"}

    @api.model
    def process_unassigned(self, message, message_dict):
        if not self.env.company.use_unassigned_mails:
            return

        values = {
            key: message_dict.get(key)
            for key in ("email_from", "message_id", "subject", "body")
        }
        if not all(values.get(k) for k in self._required_message_dict_fields()):
            return

        if self.search_count([("message_id", "=", values["message_id"])]):
            return

        rec = self.sudo().create({**values, "message": message})
        receiver = self.env["mail.unassigned.receiver"].sudo()
        for recv_type in ("cc", "to"):
            addresses = message_dict.get(recv_type) or ""
            for name, addr in email_split_tuples(addresses):
                receiver.create(
                    {"type": recv_type, "mail_id": rec.id, "name": name, "email": addr}
                )

        for attachment in message_dict.get("attachments") or []:
            if len(attachment) == 2:
                name, content = attachment
                info = {}
            elif len(attachment) == 3:
                name, content, info = attachment
            else:
                continue

            if isinstance(content, str):
                encoding = info and info.get("encoding")
                try:
                    content = content.encode(encoding or "utf-8")
                except UnicodeEncodeError:
                    content = content.encode("utf-8")
            elif isinstance(content, EmailMessage):
                content = content.as_bytes()
            elif content is None:
                continue

            self.env["ir.attachment"].sudo().create(
                {
                    "name": name,
                    "datas": base64.b64encode(content),
                    "type": "binary",
                    "description": name,
                    "res_model": rec._name,
                    "res_id": rec.id,
                }
            )

    @api.model
    def find_thread(self, message_dict, model=None, thread_id=None):
        return self.sudo()._find_thread(message_dict, model=model, thread_id=thread_id)

    @api.model
    def _find_thread(self, message_dict, model=None, thread_id=None):
        if not self.env.company.use_unassigned_mails:
            return model, thread_id

        message_id = message_dict.get("message_id")
        if (model and thread_id) or not message_id:
            return model, thread_id

        rec = self.search([("message_id", "=", message_id)])
        if rec.thread_id:
            return rec.thread_id._name, rec.thread_id.id
        return model, thread_id

    def action_unlink(self):
        self.unlink()

    def action_open(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": self._name,
            "res_id": self.id,
            "target": "new",
        }

    def action_assign(self):
        return {
            "name": _("Assign E-Mails"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.assign.wizard",
            "target": "new",
            "context": {
                "default_mail_ids": [(6, 0, self.ids)],
            },
        }

    def _assign_mail(self):
        self.ensure_one()
        return (
            self.env["mail.thread"]
            .with_context(default_fetchmail_server_id=self.fetchmail_server_id.id)
            .message_process(
                self.model or self.fetchmail_server_id.object_id.model,
                self.message,
                save_original=self.fetchmail_server_id.original,
                strip_attachments=self.fetchmail_server_id
                and not self.fetchmail_server_id.attach,
            )
        )

    def assign_mails(self):
        to_unlink = self.browse()

        domain = ["|", ("thread_id", "!=", False), ("model", "!=", False)]
        for mail in self or self.search(domain):
            thread = mail._assign_mail()

            if thread:
                to_unlink |= mail

        if to_unlink:
            to_unlink.unlink()
