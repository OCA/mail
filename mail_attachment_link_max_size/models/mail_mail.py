# Copyright 2026 Quartile (https://www.quartile.co)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import re

from odoo import models, tools


class MailMail(models.Model):
    _inherit = "mail.mail"

    def _split_by_mail_configuration(self):
        """Link heavy attachments in body_html once the mail server is known, so
        that _send() leaves them out of the email as it does for any linked one.
        """
        for (
            mail_server_id,
            smtp_from,
            batch_ids,
        ) in super()._split_by_mail_configuration():
            mail_server = self.env["ir.mail_server"].sudo().browse(mail_server_id)
            max_size = mail_server._get_max_email_size() * 1024 * 1024
            self.browse(batch_ids).sudo()._convert_attachments_to_links(max_size)
            yield mail_server_id, smtp_from, batch_ids

    def _convert_attachments_to_links(self, max_size):
        for mail in self:
            body = mail.body_html or ""
            linked_ids = {
                int(i) for i in re.findall(r"/web/(?:content|image)/([0-9]+)", body)
            }
            attachments = mail.attachment_ids.filtered(lambda a: a.id not in linked_ids)
            to_link = attachments.filtered(
                lambda a: a.res_model and a.res_id and a.res_model != "mail.message"
            )
            # Base64 codes 6 bits in 8, plus 10 KB for the headers
            size = (
                len(body.encode())
                + sum(attachments.mapped("file_size")) * 8 / 6
                + 10 * 1024
            )
            if not to_link or size <= max_size:
                continue
            to_link.generate_access_token()
            links = self.env["ir.qweb"]._render(
                "mail_attachment_link_max_size.mail_attachment_links",
                {"attachments": to_link},
            )
            mail.body_html = tools.mail.append_content_to_html(
                body, links, plaintext=False
            )
