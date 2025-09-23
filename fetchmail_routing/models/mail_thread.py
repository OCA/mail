# © 2023 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def message_find_thread_functions(self):
        return [
            self.env["mail.unassigned"].find_thread,
            self.env["fetchmail.routing"].find_thread,
        ]

    @api.model
    def message_route(
        self, message, message_dict, model=None, thread_id=None, custom_values=None
    ):
        assigned = False
        for func in self.message_find_thread_functions():
            if not model or not thread_id:
                model, thread_id = func(message_dict, model, thread_id)
                assigned = True

        # Shortcut the handling if the thread was found
        if assigned and model and thread_id:
            email_from = message_dict["email_from"]
            message_dict.pop("parent_id", None)
            user_id = self._mail_find_user_for_gateway(email_from).id or self._uid
            route = self._routing_check_route(
                message,
                message_dict,
                (model, thread_id, custom_values, user_id, None),
                raise_exception=True,
            )
            if route:
                _logger.info(
                    "Routing mail from %s to %s with Message-Id %s: fallback to "
                    "model:%s, thread_id:%s, custom_values:%s, uid:%s",
                    email_from,
                    message_dict["to"],
                    message_dict["message_id"],
                    model,
                    thread_id,
                    custom_values,
                    user_id,
                )
                return [route]

        try:
            return super().message_route(
                message,
                message_dict,
                model=model,
                thread_id=thread_id,
                custom_values=custom_values,
            )
        except ValueError:
            self.env["mail.unassigned"].process_unassigned(message, message_dict)
            return []
