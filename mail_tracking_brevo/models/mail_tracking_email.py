# Copyright 2026 CIT-Services
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
from collections import namedtuple
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import email_split

from ..wizards.res_config_settings import BREVO_TIMEOUT

_logger = logging.getLogger(__name__)

BrevoParameters = namedtuple(
    "BrevoParameters",
    (
        "api_key",
        "api_url",
        "webhook_token",
        "webhooks_domain",
    ),
)

EQUIVALENTS = {
    "request": "sent",
    "sent": "sent",
    "delivered": "delivered",
    "opened": "open",
    "first_opening": "open",
    "firstOpening": "open",
    "unique_opened": "open",
    "unique_proxy_open": "open",
    "click": "click",
    "clicked": "click",
    "clicks": "click",
    "proxy_open": "click",
    "soft_bounce": "soft_bounce",
    "softBounce": "soft_bounce",
    "deferred": "soft_bounce",
    "hard_bounce": "hard_bounce",
    "hardBounce": "hard_bounce",
    "invalid": "hard_bounce",
    "invalid_email": "hard_bounce",
    "invalidEmail": "hard_bounce",
    "spam": "spam",
    "complaint": "spam",
    "unsubscribed": "unsub",
    "blocked": "reject",
    "error": "reject",
}


class MailTrackingEmail(models.Model):
    _inherit = "mail.tracking.email"

    def _brevo_country_search(self, country_code):
        country = False
        if country_code:
            country = self.env["res.country"].search(
                [("code", "=", country_code.upper())]
            )
        if country:
            return country.id
        return False

    @api.model
    def _brevo_values(self):
        icp = self.env["ir.config_parameter"].sudo()
        api_key = icp.get_param("brevo.api_key")
        if not api_key:
            raise ValidationError(self.env._("There is no Brevo API key!"))
        api_url = icp.get_param("brevo.api_url", "https://api.brevo.com")
        webhook_token = icp.get_param("brevo.webhook_token")
        web_base_url = icp.get_param("web.base.url")
        webhooks_domain = icp.get_param("brevo.webhooks_domain", web_base_url)
        return BrevoParameters(
            api_key=api_key,
            api_url=api_url,
            webhook_token=webhook_token,
            webhooks_domain=webhooks_domain,
        )

    @api.model
    def _brevo_event2type(self, event, default="UNKNOWN"):
        """Return the `mail.tracking.event` equivalent state for Brevo webhooks."""
        event_type = event.get("event") if isinstance(event, dict) else event
        return EQUIVALENTS.get(event_type, default)

    def _brevo_metadata(self, brevo_event_type, event, metadata):
        brevo_id = (
            f"{event.get('message-id') or ''}_{event.get('event') or ''}"
            f"_{event.get('ts_event') or ''}"
        ).strip()
        if brevo_id:
            metadata["brevo_id"] = brevo_id
        ts = event.get("ts_event") or event.get("ts", False)
        try:
            ts = float(ts)
        except Exception:
            ts = False
        if not ts and event.get("date"):
            try:
                date_str = str(event["date"])
                if "T" in date_str:
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                else:
                    dt = datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S").replace(
                        tzinfo=timezone.utc
                    )
                ts = dt.timestamp()
            except Exception:
                ts = False
        if ts:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            metadata.update(
                {
                    "timestamp": ts,
                    "time": fields.Datetime.to_string(dt),
                    "date": fields.Date.to_string(dt),
                }
            )
        mapping = {
            "recipient": "email",
            "ip": "ip",
            "user_agent": "user_agent",
            "url": "link",
        }
        for k, v in mapping.items():
            if event.get(v, False):
                metadata[k] = event[v]
        metadata.update(
            {
                "mobile": event.get("device_type") in {"mobile", "tablet"},
                "user_country_id": self._brevo_country_search(
                    event.get("country", False)
                ),
            }
        )
        if brevo_event_type in (
            "soft_bounce",
            "hard_bounce",
            "invalid_email",
            "deferred",
        ):
            metadata.update(
                {
                    "error_type": brevo_event_type,
                    "error_description": event.get("reason", False),
                    "error_details": event.get("error", False)
                    or event.get("reason", False),
                }
            )
        elif brevo_event_type in ("blocked", "error"):
            metadata.update(
                {
                    "error_type": "rejected",
                    "error_description": event.get("reason", False),
                    "error_details": event.get("error", False),
                }
            )
        elif brevo_event_type in ("spam", "complaint"):
            metadata.update(
                {
                    "error_type": "spam",
                    "error_description": (
                        f"Recipient '{event.get('email', False)}' marked "
                        "this email as spam"
                    ),
                }
            )
        return metadata

    @api.model
    def _brevo_event_process(self, event_data, metadata):
        raw_custom = (
            event_data.get("X-Mailin-custom") or event_data.get("custom_data") or {}
        )
        if isinstance(raw_custom, str):
            try:
                custom_vars = json.loads(raw_custom)
            except Exception:
                custom_vars = {}
        elif isinstance(raw_custom, dict):
            custom_vars = raw_custom
        else:
            custom_vars = {}
        if (
            custom_vars.get("odoo_db")
            and custom_vars.get("odoo_db") != self.env.cr.dbname
        ):
            _logger.error(
                "Brevo: event for DB %s received in DB %s: %s",
                custom_vars["odoo_db"],
                self.env.cr.dbname,
                event_data,
            )
            return
        brevo_id = (
            f"{event_data.get('message-id') or ''}_{event_data.get('event') or ''}"
            f"_{event_data.get('ts_event') or ''}"
        ).strip()
        if brevo_id:
            db_event = self.env["mail.tracking.event"].search(
                [("brevo_id", "=", brevo_id)], limit=1
            )
            if db_event:
                _logger.debug("Brevo event already found in DB: %s", brevo_id)
                return db_event
        tracking_email_id = custom_vars.get("tracking_email_id")
        tracking_email = (
            self.browse(int(tracking_email_id)) if tracking_email_id else False
        )
        if not tracking_email or not tracking_email.exists():
            message_id = event_data.get("message-id") or event_data.get("messageId", "")
            if message_id:
                clean_msg_id = message_id.replace("<", "").replace(">", "").strip()
                tracking_email = self.search(
                    [("message_id", "ilike", clean_msg_id)], limit=1
                )
        if not tracking_email or not tracking_email.exists():
            _logger.debug("Brevo: tracking email not found for event: %s", event_data)
            return
        message_id = event_data.get("message-id") or event_data.get("messageId", "")
        recipient = event_data.get("email", "")
        brevo_event_type = event_data.get("event", "")
        state = self._brevo_event2type(event_data, brevo_event_type)
        metadata = self._brevo_metadata(brevo_event_type, event_data, metadata)
        _logger.info(
            "Importing Brevo event %s (%s message %s for %s)",
            brevo_id,
            brevo_event_type,
            message_id,
            recipient,
        )
        prev_state = tracking_email.state
        event_ids = tracking_email.event_create(state, metadata)
        state_precedence = {
            "error": 10,
            "sent": 10,
            "deferred": 20,
            "delivered": 30,
            "opened": 40,
            "unsub": 40,
            "click": 50,
            "soft-bounced": 50,
            "bounced": 50,
            "spam": 50,
            "rejected": 50,
        }
        if state_precedence.get(prev_state, 0) > state_precedence.get(
            tracking_email.state, 0
        ):
            tracking_email.sudo().write({"state": prev_state})
        return event_ids

    @api.model
    def _brevo_extract_event_ts(self, ev):
        ts_val = ev.get("ts_event") or ev.get("ts")
        if ts_val:
            try:
                return float(ts_val)
            except (ValueError, TypeError) as err:
                _logger.debug(
                    "Error parsing Brevo event timestamp value %s: %s", ts_val, err
                )
        if ev.get("date"):
            try:
                d_str = str(ev["date"])
                if "T" in d_str:
                    return datetime.fromisoformat(
                        d_str.replace("Z", "+00:00")
                    ).timestamp()
                return (
                    datetime.strptime(d_str[:19], "%Y-%m-%d %H:%M:%S")
                    .replace(tzinfo=timezone.utc)
                    .timestamp()
                )
            except (ValueError, TypeError) as err:
                _logger.debug(
                    "Error parsing Brevo event date %s: %s", ev.get("date"), err
                )
        return 0.0

    def _brevo_fetch_events_for_tracking(self, tracking, params_info, headers, timeout):
        clean_msg_id = tracking.message_id.replace("<", "").replace(">", "").strip()
        recipient_email = (
            email_split(tracking.recipient)[0] if tracking.recipient else False
        )
        events = []
        url = urljoin(params_info.api_url, "/v3/smtp/statistics/events")
        offset = 0
        limit = 50
        while True:
            params = {
                "limit": limit,
                "offset": offset,
            }
            if recipient_email:
                params["email"] = recipient_email
            res = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=timeout,
            )
            if not res or res.status_code != 200:
                raise UserError(self.env._("Couldn't retrieve Brevo information"))
            iter_events = res.json().get("events", [])
            if not iter_events:
                break
            for ev in iter_events:
                ev_msg_id = (
                    (ev.get("messageId") or ev.get("message-id") or "")
                    .replace("<", "")
                    .replace(">", "")
                    .strip()
                )
                custom_data_raw = (
                    ev.get("X-Mailin-custom") or ev.get("custom_data") or ""
                )
                custom_data_str = (
                    json.dumps(custom_data_raw)
                    if isinstance(custom_data_raw, dict)
                    else str(custom_data_raw)
                )

                matches_msg_id = bool(ev_msg_id and ev_msg_id == clean_msg_id)
                matches_tracking_id = (
                    f'"tracking_email_id": {tracking.id}' in custom_data_str
                    or f'"tracking_email_id":"{tracking.id}"' in custom_data_str
                )

                if matches_msg_id or matches_tracking_id or not ev_msg_id:
                    events.append(ev)
            if len(iter_events) < limit:
                break
            offset += limit
        return events

    def action_manual_check_brevo(self):
        timeout = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("brevo.timeout", BREVO_TIMEOUT)
        )
        params_info = self._brevo_values()
        headers = {
            "api-key": params_info.api_key,
            "accept": "application/json",
        }
        for tracking in self.filtered("message_id"):
            events = self._brevo_fetch_events_for_tracking(
                tracking, params_info, headers, timeout
            )
            if not events:
                raise UserError(
                    self.env._(
                        "No tracking events found in Brevo for this email yet. "
                        "Please try again in a few moments."
                    )
                )

            events.sort(key=self._brevo_extract_event_ts)
            for event in events:
                if "X-Mailin-custom" not in event and "custom_data" not in event:
                    event["custom_data"] = {
                        "odoo_db": self.env.cr.dbname,
                        "tracking_email_id": tracking.id,
                    }
                self.sudo()._brevo_event_process(event, {})
