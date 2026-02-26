# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class MailboxControllerExtended(http.Controller):
    @http.route(
        "/mail/sent_history/messages", methods=["POST"], type="json", auth="user"
    )
    def discuss_sent_history_messages(
        self, search_term=None, before=None, after=None, limit=30, around=None
    ):
        partner_id = request.env.user.partner_id.id
        domain = [("author_id", "=", partner_id), ("message_type", "in", ["comment"])]
        res = request.env["mail.message"]._message_fetch(
            domain,
            search_term=search_term,
            before=before,
            after=after,
            around=around,
            limit=limit,
        )
        return {**res, "messages": res["messages"].message_format()}
