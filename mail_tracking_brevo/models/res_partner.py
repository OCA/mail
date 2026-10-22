# Copyright 2026 CIT-Services
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from urllib.parse import quote, urljoin

import requests
from markupsafe import Markup

from odoo import SUPERUSER_ID, models

from ..wizards.res_config_settings import BREVO_TIMEOUT


class ResPartner(models.Model):
    _inherit = "res.partner"

    def email_bounced_set(self, tracking_emails, reason, event=None):
        res = super().email_bounced_set(tracking_emails, reason, event=event)
        self._brevo_email_bounced_set(reason, event)
        return res

    def _brevo_email_bounced_set(self, reason, event):
        for partner in self:
            if not partner.email:
                continue
            event = event or self.env["mail.tracking.event"]
            event_str = (
                event._get_html_link(title=event.id) if event else self.env._("unknown")
            )
            body = Markup(
                self.env._(
                    "Email has been bounced: %(email)s\nReason: "
                    "%(reason)s\nEvent: %(event_str)s",
                    email=partner.email,
                    reason=reason,
                    event_str=event_str,
                )
            )
            if self.env.su:
                partner = partner.with_user(SUPERUSER_ID)
            partner.message_post(body=body)

    def brevo_check_email_bounced(self):
        """Checks if the partner's email is blacklisted in Brevo.
        API documentation:
        https://developers.brevo.com/reference/getcontactinfo
        """
        params_info = self.env["mail.tracking.email"]._brevo_values()
        timeout = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("brevo.timeout", BREVO_TIMEOUT)
        )
        headers = {
            "api-key": params_info.api_key,
            "accept": "application/json",
        }
        for partner in self.filtered("email"):
            encoded_email = quote(partner.email)
            url = urljoin(params_info.api_url, f"/v3/contacts/{encoded_email}")
            res = requests.get(url, headers=headers, timeout=timeout)
            if res.status_code == 200:
                partner.email_bounced = res.json().get("emailBlacklisted", False)
            elif res.status_code == 404:
                partner.email_bounced = False

    def force_set_bounced(self):
        """Forces partner's email into Brevo's blacklist.
        API documentation:
        https://developers.brevo.com/reference/updatecontact
        """
        params_info = self.env["mail.tracking.email"]._brevo_values()
        timeout = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("brevo.timeout", BREVO_TIMEOUT)
        )
        headers = {
            "api-key": params_info.api_key,
            "Content-Type": "application/json",
            "accept": "application/json",
        }
        for partner in self.filtered("email"):
            encoded_email = quote(partner.email)
            url = urljoin(params_info.api_url, f"/v3/contacts/{encoded_email}")
            res = requests.put(
                url,
                headers=headers,
                json={"emailBlacklisted": True},
                timeout=timeout,
            )
            if res.status_code in (200, 204):
                partner.email_bounced = True

    def force_unset_bounced(self):
        """Forces partner's email removal from Brevo's blacklist.
        API documentation:
        https://developers.brevo.com/reference/updatecontact
        """
        params_info = self.env["mail.tracking.email"]._brevo_values()
        timeout = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("brevo.timeout", BREVO_TIMEOUT)
        )
        headers = {
            "api-key": params_info.api_key,
            "Content-Type": "application/json",
            "accept": "application/json",
        }
        for partner in self.filtered("email"):
            encoded_email = quote(partner.email)
            url = urljoin(params_info.api_url, f"/v3/contacts/{encoded_email}")
            res = requests.put(
                url,
                headers=headers,
                json={"emailBlacklisted": False},
                timeout=timeout,
            )
            if res.status_code in (200, 204, 404):
                partner.email_bounced = False
