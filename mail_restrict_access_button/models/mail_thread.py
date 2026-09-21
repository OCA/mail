# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_get_recipients_groups_fillup(
        self, groups, model_description, msg_vals=None
    ):
        groups = groups + [
            [
                "unregistered_external",
                lambda recipient: recipient["type"] == "customer",
                {"has_button_access": False},
            ]
        ]
        groups = super()._notify_get_recipients_groups_fillup(
            groups, model_description, msg_vals=msg_vals
        )
        for index, (name, matches_recipient, group_data) in enumerate(groups):
            if group_data.get("has_button_access") and group_data.get("active"):
                groups[index] = [
                    name,
                    self._without_unregistered(matches_recipient),
                    group_data,
                ]
        return groups

    @staticmethod
    def _without_unregistered(matches_recipient):
        # Wrap a group's matching conditions so it never matches unregistered
        # external partners (without user account)
        def predicate(recipient):
            return matches_recipient(recipient) and recipient["type"] != "customer"

        return predicate
