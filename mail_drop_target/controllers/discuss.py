# Copyright Nguyen Minh Chien (chien@trobz.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.tools.translate import _

from odoo.addons.mail.controllers import attachment


class AttachmentController(attachment.AttachmentController):
    @http.route("/mail/attachment/upload", methods=["POST"], type="http", auth="public")
    def mail_attachment_upload(
        self, ufile, thread_id, thread_model, is_pending=False, **kwargs
    ):
        if not is_pending or is_pending == "false":
            # Add this point, make sure the message related to the uploaded
            # file does exist.
            resp = self.mail_attachment_upload_email(ufile, thread_id, thread_model)
            if resp:
                return resp

        return super().mail_attachment_upload(
            ufile, thread_id, thread_model, is_pending, **kwargs
        )

    def mail_attachment_upload_email(self, ufile, thread_id, thread_model):
        attachment_model = request.env["ir.attachment"]
        if thread_model == "discuss.channel":
            post_access = (
                request.env[thread_model]
                .sudo()
                ._get_mail_message_access(int(thread_id), "create")
            )
            channel = request.env[thread_model]._get_thread_with_access(
                int(thread_id), mode=post_access
            )
            if not channel:
                # Let the standard upload deal with the missing access
                return False
            # sudo: ir.attachment - reading an email file posted on an
            # accessible channel, as members may not read its messages
            attachment_model = attachment_model.sudo()
        try:
            mail_resp = attachment_model.read_mail_file_content(
                ufile.filename, ufile.read(), int(thread_id), thread_model
            )
            ufile.seek(0)
            if not mail_resp:
                return False
            responseData = {"email_upload": 1}
        except AccessError:
            message = _("You are not allowed to upload an attachment here.")
            responseData = {"error": {"message": message}}
        except UserError as err:
            responseData = {"error": {"message": str(err)}}
        return request.make_json_response(responseData)
