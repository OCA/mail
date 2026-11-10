# Copyright 2026 CIT-Services
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from werkzeug.exceptions import NotAcceptable

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.mail_tracking.controllers import main
from odoo.addons.web.controllers.utils import ensure_db

_logger = logging.getLogger(__name__)


class MailTrackingController(main.MailTrackingController):
    def _mail_tracking_brevo_webhook_verify(self, expected_token, kwargs):
        """Avoid brevo webhook attacks."""
        if not expected_token:
            return
        token = request.params.get("token") or kwargs.get("token")
        if token != expected_token:
            _logger.warning("Brevo webhook rejected: invalid token")
            raise ValidationError(request.env._("Invalid webhook token"))

    @http.route(
        ["/mail/tracking/brevo/all"],
        auth="none",
        type="http",
        csrf=False,
        methods=["POST", "GET"],
    )
    def mail_tracking_brevo_webhook(self, **kwargs):
        """Process webhooks from Brevo.
        See https://app.brevo.com/app-store/webhooks,
        https://help.brevo.com/hc/en-us/articles/27824932835474-Create-outbound-webhooks-to-send-real-time-data-from-Brevo-to-an-external-app
        """  # noqa: E501
        ensure_db()
        icp = request.env["ir.config_parameter"].sudo()
        try:
            self._mail_tracking_brevo_webhook_verify(
                icp.get_param("brevo.webhook_token"), kwargs
            )
        except ValidationError as error:
            raise NotAcceptable from error

        try:
            event_data = request.get_json_data() or {}
        except Exception:
            event_data = {}
        if not event_data:
            _logger.debug("Brevo webhook received empty data")
            return request.make_response("OK", [("Content-Type", "text/plain")])

        tracking_email_obj = request.env["mail.tracking.email"].sudo()
        request_metadata = self._request_metadata()

        if isinstance(event_data, list):
            for event in event_data:
                if isinstance(event, dict):
                    tracking_email_obj._brevo_event_process(event, request_metadata)
        elif isinstance(event_data, dict):
            tracking_email_obj._brevo_event_process(event_data, request_metadata)

        return request.make_response("OK", [("Content-Type", "text/plain")])
