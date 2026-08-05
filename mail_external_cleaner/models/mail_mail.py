# Copyright 2025 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io
import re

from odoo import models
from odoo.tools.mimetypes import guess_mimetype

IMAGE_REGEX = (
    r"(\<img [\w\b =\-\":;,.%]*src=\")(https?:\/\/[\w.:]+)"
    r"((?:\/[\w@:%.+&~#=\/-]+)?(?:\?\S+)?)(\"[\w\b =\-\":;,.%]+\/?\>)"
)


class MailMail(models.Model):
    _inherit = "mail.mail"

    def _send_prepare_body(self):
        body = super()._send_prepare_body()
        return self._embed_images(body)

    def _get_image_attachment(self, path):
        if m := re.match(r"\/logo\.png\?company=(\d+)", path):
            company = self.env["res.company"].browse(int(m.group(1)))
            image_base64 = base64.b64decode(company.logo_web)
            io.BytesIO(image_base64)
            mimetype = guess_mimetype(image_base64, default="image/png")
            imgext = "." + mimetype.split("/")[1]
            if imgext == ".svg+xml":
                imgext = ".svg"
            return mimetype, company.logo_web.decode("utf-8")
        if m := re.match(r"\/web\/image\/(\d+)", path):
            image = self.env["ir.attachment"].browse(int(m.group(1)))
            if image.exists():
                return image.mimetype, image.datas.decode("utf-8")

    def _embed_images(self, body):
        base_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("web.base.url", default="http://localhost:8069")
        )
        for data in set(
            re.findall(
                IMAGE_REGEX,
                body,
            )
        ):
            pre_data, url, path, post_data = data
            if url == base_url:
                img_data = f"{pre_data}{url}{path}{post_data}"
                attachment = self._get_image_attachment(path)
                if attachment:
                    body = body.replace(
                        img_data,
                        (
                            f"{pre_data}data:{attachment[0]};"
                            f"base64,{attachment[1]}{post_data}"
                        ),
                    )
        return body
