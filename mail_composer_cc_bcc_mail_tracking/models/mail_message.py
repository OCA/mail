# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = "mail.message"

    def tracking_status(self):
        res = super().tracking_status()

        # Flag each recipient as Cc/Bcc using the
        # partner-based recipient_cc_ids / recipient_bcc_ids
        # (authoritative, set by the mail composer).
        # Recipients themselves are already listed
        # by super() through notified_partner_ids.
        to_ids = set(self.partner_ids.ids)
        cc_ids = set(self.recipient_cc_ids.ids)
        bcc_ids = set(self.recipient_bcc_ids.ids)
        for tracking in res:
            pid = tracking.get("partner_id")
            is_cc = pid in cc_ids
            is_bcc = pid in bcc_ids
            # A recipient is "To" when explicitly in partner_ids, or when it is
            # neither Cc nor Bcc (followers / notified partners). A partner may
            # belong to several lists at once.
            tracking.update(
                {
                    "isTo": pid in to_ids or not (is_cc or is_bcc),
                    "isCc": is_cc,
                    "isBcc": is_bcc,
                }
            )
        return res

    def _recipients_display_company(self):
        """Company whose settings drive the chatter recipients display."""
        self.ensure_one()
        return self.record_company_id or self.env.company

    def _recipients_default_expanded(self):
        """Whether the To/Cc/Bcc split is shown by default (else single 'To')."""
        self.ensure_one()
        company = self._recipients_display_company()
        return company.chatter_recipients_default_display == "expanded"

    def _recipients_allow_toggle(self):
        """Whether the user may switch between the collapsed and expanded views."""
        self.ensure_one()
        return self._recipients_display_company().chatter_recipients_allow_toggle

    def _extras_to_store(self, store: Store, format_reply):
        res = super()._extras_to_store(store, format_reply=format_reply)
        for message in self:
            store.add(
                message,
                {
                    "recipientsDefaultExpanded": message._recipients_default_expanded(),
                    "recipientsAllowToggle": message._recipients_allow_toggle(),
                },
            )
        return res
