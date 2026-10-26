# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright 2026 Quartile (https://www.quartile.co)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import json
import re

from odoo import api, models, tools


class MailMail(models.Model):
    _inherit = "mail.mail"

    @api.model
    def _estimate_email_size(self, headers, body, attachments_size):
        """Estimate the email size, incorporating a small added security margin.

        :param dict headers: email headers
        :param str body: email body
        :param list attachments_size: list of attachment size in bytes
        """
        return (
            len(json.dumps(headers or {}, ensure_ascii=False).encode(errors="ignore"))
            + len((body or "").encode(errors="ignore"))
            # 8 / 6 factor because base 64 are 6 bits coded in 8 bits
            + sum(attachments_size) * 8 / 6
            # adding 10Ko as security
            + 10 * 1024
        )

    def _split_by_mail_configuration(self):
        for (
            mail_server_id,
            smtp_from,
            batch_ids,
        ) in super()._split_by_mail_configuration():
            mail_server = self.env["ir.mail_server"].browse(mail_server_id)
            for mail in self.browse(batch_ids).sudo():
                mail._convert_attachments_to_links(mail_server)
            yield mail_server_id, smtp_from, batch_ids

    def _convert_attachments_to_links(self, mail_server=False):
        self.ensure_one()
        body = self.body_html or ""

        attachments = self.attachment_ids
        # Prepare attachments:
        # Remove attachments if user send the link with the access_token.
        if body and attachments:
            link_ids = {
                int(link)
                for link in re.findall(r"/web/(?:content|image)/([0-9]+)", body)
            }
            if link_ids:
                attachments = attachments - self.env["ir.attachment"].browse(
                    list(link_ids)
                )

        # Turn remaining attachments into links if they are too heavy and
        # their ownership are business models (i.e. something != mail.message,
        # otherwise they will be deleted along with the mail message leading to a 404)
        if record_owned_attachments := attachments.sudo().filtered(
            lambda a: a.res_model and a.res_id and a.res_model != "mail.message"
        ):
            estimated_email_size_bytes = self._estimate_email_size(
                self.headers, body, [a.file_size for a in attachments.sudo()]
            )
            max_email_size_bytes = (
                (mail_server or self.env["ir.mail_server"]).sudo()._get_max_email_size()
                * 1024
                * 1024
            )
            if estimated_email_size_bytes > max_email_size_bytes:
                # Remove attachments and prepare downloadable links to be added in the body
                record_owned_attachments.sudo().generate_access_token()
                attachments_links = self.env["ir.qweb"]._render(
                    "mail_max_email_size.mail_attachment_links",
                    {"attachments": record_owned_attachments},
                )
                self.body_html = tools.mail.append_content_to_html(
                    body, attachments_links, plaintext=False
                )
