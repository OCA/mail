# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Override the Outlook OAuth callback to support personal mail servers.

The v18 core callback (a) only allows ``base.group_system`` users and (b) does
not activate the record. For a personal server connected by a regular user we
must instead authorize the *owner* of the server and un-archive it once the
tokens have been fetched.
"""

import json
import logging

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq

from odoo.addons.microsoft_outlook.controllers.main import (
    MicrosoftOutlookController,
)

_logger = logging.getLogger(__name__)


class MicrosoftOutlookPersonalController(MicrosoftOutlookController):
    @http.route("/microsoft_outlook/confirm", type="http", auth="user")
    def microsoft_outlook_callback(
        self, code=None, state=None, error_description=None, **kwargs
    ):
        try:
            state = json.loads(state)
            model_name = state["model"]
            rec_id = state["id"]
            csrf_token = state["csrf_token"]
        except Exception:
            _logger.error("Microsoft Outlook: Wrong state value %r.", state)
            raise Forbidden() from None

        model = request.env[model_name]
        if not isinstance(model, request.env.registry["microsoft.outlook.mixin"]):
            raise Forbidden()

        record = model.browse(rec_id).sudo().exists()
        if not record:
            raise Forbidden()

        # Authorize: system administrators, or the owner of a personal server.
        is_owner = (
            record._name == "ir.mail_server"
            and record.owner_user_id.id == request.env.user.id
        )
        if not request.env.user.has_group("base.group_system") and not is_owner:
            _logger.error(
                "Microsoft Outlook: %s is not allowed to link %s#%s.",
                request.env.user.login,
                model_name,
                rec_id,
            )
            raise Forbidden()

        if not csrf_token or not consteq(csrf_token, record._get_outlook_csrf_token()):
            _logger.error("Microsoft Outlook: Wrong CSRF token during authentication.")
            raise Forbidden()

        if error_description:
            return request.render(
                "microsoft_outlook.microsoft_outlook_oauth_error",
                {
                    "error": error_description,
                    "model_name": model_name,
                    "rec_id": rec_id,
                },
            )

        try:
            refresh_token, access_token, expiration = (
                record._fetch_outlook_refresh_token(code)
            )
        except UserError as e:
            return request.render(
                "microsoft_outlook.microsoft_outlook_oauth_error",
                {
                    "error": str(e),
                    "model_name": model_name,
                    "rec_id": rec_id,
                },
            )

        record.write(
            {
                "active": True,
                "microsoft_outlook_refresh_token": refresh_token,
                "microsoft_outlook_access_token": access_token,
                "microsoft_outlook_access_token_expiration": expiration,
            }
        )

        if is_owner:
            return request.redirect(f"/odoo/my-preferences/{request.env.user.id}")
        return request.redirect(f"/odoo/{model_name}/{rec_id}")
