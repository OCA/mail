# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.fields import Domain


class MailFollowers(models.Model):
    _inherit = "mail.followers"

    def _insert_followers(
        self,
        res_model,
        res_ids,
        partner_ids,
        subtypes=None,
        customer_ids=None,
        check_existing=True,
        existing_policy="skip",
    ):
        """Drop partners that do not meet the configured follower domain.

        Every follower creation of ``mail.thread`` ends up here: explicit
        subscriptions (``message_subscribe``, the followers wizard, the
        recipients of a posted message, ...) as well as automatic ones
        (``_message_auto_subscribe``: assignees / responsible users and
        followers propagated from a parent record). Enforcing the rule at
        this level keeps a single, consistent behavior.

        Pass ``no_restrict_follower`` in the context to bypass the check.
        """
        if partner_ids and not self.env.context.get("no_restrict_follower"):
            partner_ids = self._mail_restrict_follower_selection_filter_partners(
                res_model, res_ids, partner_ids
            )
            if subtypes:
                subtypes = {
                    pid: subtypes[pid] for pid in partner_ids if pid in subtypes
                }
        return super()._insert_followers(
            res_model,
            res_ids,
            partner_ids,
            subtypes=subtypes,
            customer_ids=customer_ids,
            check_existing=check_existing,
            existing_policy=existing_policy,
        )

    @api.model
    def _mail_restrict_follower_selection_filter_partners(
        self, res_model, res_ids, partner_ids
    ):
        """Return the subset of ``partner_ids`` allowed as followers.

        The domain applies to everyone, including the current user (creator
        subscription, "Follow" button, author of a message). Partners already
        following all ``res_ids`` are kept regardless of the domain, so that
        their subscription (e.g. subtypes) can still be edited: the module
        never changes existing followers.
        """
        partner_ids = list(partner_ids)
        domain = self.env[
            "mail.followers.edit"
        ]._mail_restrict_follower_selection_get_domain(res_model)
        if domain.is_true():
            return partner_ids
        allowed_ids = set(
            self.env["res.partner"]
            .sudo()
            .search(Domain.AND([[("id", "in", partner_ids)], domain]))
            .ids
        )
        rejected_ids = set(partner_ids) - allowed_ids
        if rejected_ids and res_ids:
            follow_counts = self.sudo()._read_group(
                [
                    ("res_model", "=", res_model),
                    ("res_id", "in", list(res_ids)),
                    ("partner_id", "in", list(rejected_ids)),
                ],
                groupby=["partner_id"],
                aggregates=["res_id:count_distinct"],
            )
            allowed_ids.update(
                partner.id
                for partner, count in follow_counts
                if count == len(set(res_ids))
            )
        return [pid for pid in partner_ids if pid in allowed_ids]
