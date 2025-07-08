# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from ast import literal_eval

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    extra_headers = fields.Text(
        default="{}",
        help="""Python dictionary, e.g. {"MY-HEADER": "test"}""",
    )

    @api.constrains("extra_headers")
    def _check_extra_headers(self):
        for rec in self:
            if not rec.extra_headers:
                continue
            try:
                headers = literal_eval(rec.extra_headers)
            except SyntaxError as e:
                raise ValidationError(
                    _("The extra headers cannot be read (syntax error).")
                ) from e
            if (
                not isinstance(headers, dict)
                or any(not isinstance(k, str) for k in headers.keys())
                or any(not isinstance(v, str) for v in headers.values())
            ):
                raise ValidationError(
                    _("The extra headers must be a dictionary of strings.")
                )

    @api.model
    def send_email(
        self,
        message,
        mail_server_id=None,
        smtp_server=None,
        smtp_port=None,
        smtp_user=None,
        smtp_password=None,
        smtp_encryption=None,
        smtp_ssl_certificate=None,
        smtp_ssl_private_key=None,
        smtp_debug=False,
        smtp_session=None,
    ):
        # OVERRIDE: Inject the extra headers
        # Replicate logic from core to identify the mail server to use
        # https://github.com/odoo/odoo/blob/743369f8/odoo/addons/base/models/ir_mail_server.py/#L376-L385
        mail_server = (
            # If the server is given, use it
            self.sudo().browse(mail_server_id)
            if mail_server_id
            # If no smtp credentials are given, find it based on the From address
            else self.sudo()._find_mail_server(message["From"])[0]
            if not smtp_server
            # Otherwise it's unknown
            else self.env["ir.mail_server"]
        )
        # Inject the extra headers defined in the email server
        if mail_server:
            mail_server._add_extra_headers(message)

        return super().send_email(
            message,
            mail_server_id=mail_server_id,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            smtp_encryption=smtp_encryption,
            smtp_ssl_certificate=smtp_ssl_certificate,
            smtp_ssl_private_key=smtp_ssl_private_key,
            smtp_debug=smtp_debug,
            smtp_session=smtp_session,
        )

    def _add_extra_headers(self, message):
        self.ensure_one()
        if not self.extra_headers:
            return
        extra_headers = literal_eval(self.extra_headers)
        for key, value in extra_headers.items():
            message.add_header(key, value)
