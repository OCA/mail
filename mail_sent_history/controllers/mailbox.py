# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request

from odoo.addons.mail.tools.discuss import Store


class MailboxControllerExtended(http.Controller):
    @http.route(
        "/mail/sent_history/messages",
        methods=["POST"],
        type="jsonrpc",
        auth="user",
        readonly=True,
    )
    def discuss_sent_history_messages(self, fetch_params=None):
        partner_id = request.env.user.partner_id.id
        domain = [
            ("author_id", "=", partner_id),
            ("message_type", "in", ["comment"]),
        ]
        res = request.env["mail.message"]._message_fetch(domain, **(fetch_params or {}))
        messages = res.pop("messages")._filter_existing_records()
        return {
            **res,
            "data": Store().add(messages).get_result(),
            "messages": messages.ids,
        }
