# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.mail.controllers.thread import ThreadController


class MailRestrictFollowerThreadController(ThreadController):
    @http.route()
    def mail_thread_subscribe(self, res_model, res_id, partner_ids):
        """Tell the user why clicking "Follow" has no effect.

        Programmatic subscriptions silently skip partners that do not meet
        the follower domain; this route is the explicit "Follow" button, so
        raise instead of leaving the button unchanged without feedback.
        """
        if not request.env.context.get("no_restrict_follower"):
            allowed_ids = request.env[
                "mail.followers"
            ]._mail_restrict_follower_selection_filter_partners(
                res_model, [res_id], partner_ids
            )
            if set(partner_ids) - set(allowed_ids):
                raise UserError(
                    request.env._(
                        "You are not allowed to follow this record: the "
                        "configured follower restriction excludes you."
                    )
                )
        return super().mail_thread_subscribe(res_model, res_id, partner_ids)
