# Copyright 2026 CIT Services
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from urllib.parse import urljoin

import requests

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
# List of events expected by Brevo webhooks for type Transaction.
# https://developers.brevo.com/reference/create-webhook#request.body.events
BREVO_WEBHOOK_EVENTS = [
    "delivered",
    "hardBounce",
    "softBounce",
    "blocked",
    "spam",
    "opened",
    "uniqueOpened",
    "click",
    "invalid",
    "deferred",
    "unsubscribed",
]
# Default Brevo timeout when no parameter is set
BREVO_TIMEOUT = 10


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mail_tracking_brevo_enabled = fields.Boolean(
        string="Enable mail tracking with Brevo",
        help="Enable to enhance mail tracking with Brevo",
    )
    mail_tracking_brevo_api_key = fields.Char(
        string="Brevo API key",
        config_parameter="brevo.api_key",
        help="Secret API key used to authenticate with Brevo.",
    )
    mail_tracking_brevo_webhook_token = fields.Char(
        string="Brevo webhook token",
        config_parameter="brevo.webhook_token",
        help="Token used to validate webhooks.",
    )
    mail_tracking_brevo_webhooks_domain = fields.Char(
        string="Brevo webhooks domain",
        config_parameter="brevo.webhooks_domain",
        help="Base URL for Brevo webhooks (defaults to web.base.url if empty).",
    )
    mail_tracking_brevo_webhooks_registered = fields.Boolean(
        string="Brevo webhooks registered",
        readonly=True,
    )

    def get_values(self):
        """Is Brevo enabled?"""
        result = super().get_values()
        result["mail_tracking_brevo_enabled"] = bool(
            self.env["ir.config_parameter"].get_param("brevo.api_key")
        )
        result["mail_tracking_brevo_webhooks_registered"] = bool(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("brevo.webhooks_registered")
        )
        return result

    def mail_tracking_brevo_register_webhooks(self):
        """Register Brevo webhooks to get mail statuses automatically.
        Refer link: https://developers.brevo.com/reference/create-webhook.
        """
        params = self.env["mail.tracking.email"]._brevo_values()
        timeout = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("brevo.timeout", BREVO_TIMEOUT)
        )
        odoo_webhook = urljoin(
            params.webhooks_domain,
            f"/mail/tracking/brevo/all?db={self.env.cr.dbname}",
        )
        if params.webhook_token:
            odoo_webhook = f"{odoo_webhook}&token={params.webhook_token}"
        headers = {
            "api-key": params.api_key,
            "Content-Type": "application/json",
            "accept": "application/json",
        }
        payload = {
            "url": odoo_webhook,
            "description": f"Odoo Mail Tracking ({self.env.cr.dbname})",
            "events": BREVO_WEBHOOK_EVENTS,
            "type": "transactional",
        }
        _logger.info("Registering Brevo webhook URL: %s", odoo_webhook)
        response = requests.post(
            urljoin(params.api_url, "/v3/webhooks"),
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        try:
            response.raise_for_status()
            self.env["ir.config_parameter"].sudo().set_param(
                "brevo.webhooks_registered", True
            )
        except requests.exceptions.HTTPError as err:
            _logger.error("Error registering Brevo webhook: %s", response.text)
            raise UserError(
                self.env._("Brevo API error: %s") % (response.text or err)
            ) from err

    def mail_tracking_brevo_unregister_webhooks(self):
        """Remove existing Brevo webhooks for this database."""
        params = self.env["mail.tracking.email"]._brevo_values()
        timeout = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("brevo.timeout", BREVO_TIMEOUT)
        )
        headers = {
            "api-key": params.api_key,
            "accept": "application/json",
        }
        _logger.info("Getting current Brevo webhooks")
        response = requests.get(
            urljoin(params.api_url, "/v3/webhooks?type=transactional"),
            headers=headers,
            timeout=timeout,
        )
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            _logger.error("Error listing Brevo webhooks: %s", response.text)
            raise UserError(
                self.env._("Brevo API error: %s") % (response.text or err)
            ) from err
        webhooks = response.json().get("webhooks", [])
        base_odoo_webhook = urljoin(
            params.webhooks_domain,
            f"/mail/tracking/brevo/all?db={self.env.cr.dbname}",
        )
        for hook in webhooks:
            if base_odoo_webhook in hook.get("url", ""):
                webhook_id = hook["id"]
                _logger.info(
                    "Deleting Brevo webhook ID: %s (URL: %s)", webhook_id, hook["url"]
                )
                del_response = requests.delete(
                    urljoin(params.api_url, f"/v3/webhooks/{webhook_id}"),
                    headers=headers,
                    timeout=timeout,
                )
                try:
                    del_response.raise_for_status()
                except requests.exceptions.HTTPError as err:
                    _logger.error(
                        "Error deleting Brevo webhook %s: %s",
                        webhook_id,
                        del_response.text,
                    )
                    raise UserError(
                        self.env._("Brevo API error: %s") % (del_response.text or err)
                    ) from err
        self.env["ir.config_parameter"].sudo().set_param(
            "brevo.webhooks_registered", False
        )
