from odoo import fields, models
from odoo.fields import Domain


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    message_partner_ids = fields.Many2many(
        domain=lambda thread: thread.env[
            "mail.followers.edit"
        ]._mail_restrict_follower_selection_get_domain(thread._name)
    )

    def message_subscribe(self, partner_ids=None, subtype_ids=None):
        """Drop partners that do not meet the configured follower domain.

        Many models subscribe partners programmatically (customer of a ticket,
        lead or order, recipients of a posted message, senders of incoming
        mails, ...) without going through the followers wizard, so the
        restriction has to be enforced here to be effective.

        Pass ``no_restrict_follower`` in the context to bypass the check.
        """
        if partner_ids and not self.env.context.get("no_restrict_follower"):
            partner_ids = self._mail_restrict_follower_selection_filter_partners(
                partner_ids
            )
        return super().message_subscribe(
            partner_ids=partner_ids, subtype_ids=subtype_ids
        )

    def _mail_restrict_follower_selection_filter_partners(self, partner_ids):
        """Return the subset of ``partner_ids`` allowed as followers of ``self``.

        The partner of the current user is always kept: following the records
        one works on is a read-level action in Odoo and must not depend on
        the follower domain.
        """
        partner_ids = list(partner_ids)
        domain = self.env[
            "mail.followers.edit"
        ]._mail_restrict_follower_selection_get_domain(self._name)
        if domain.is_true():
            return partner_ids
        allowed_ids = set(
            self.env["res.partner"]
            .sudo()
            .search(Domain.AND([[("id", "in", partner_ids)], domain]))
            .ids
        )
        allowed_ids.add(self.env.user.partner_id.id)
        return [pid for pid in partner_ids if pid in allowed_ids]
