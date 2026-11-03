from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_get_recipients(self, message, **kwargs):
        """Inherit this method to add in the list of partners to be notify
        the forwarding_partner_id of any partners in the list"""
        recipient_data = super()._notify_get_recipients(message, **kwargs)
        if not recipient_data:
            return recipient_data
        partner_dict = {x["id"]: x for x in recipient_data if x.get("id")}
        # forwarding partner id -> data of the partner it forwards for
        forwarded = {}
        # for each partner being notified we check if it has a
        # forwarding_partner_id configured that is not being notified yet
        for partner in (
            self.env["res.partner"]
            .sudo()
            .with_context(prefetch_fields=False)
            .browse(partner_dict.keys())
        ):
            forwarding_id = partner.forwarding_partner_id.id
            if (
                forwarding_id
                and forwarding_id not in partner_dict
                and forwarding_id not in forwarded
            ):
                forwarded[forwarding_id] = partner_dict[partner.id]
        if not forwarded:
            return recipient_data
        msg_sudo = message.sudo()
        # use the forwarding partners' own data (user, groups, share, email...)
        forwarding_data = self.env["mail.followers"]._get_recipient_data(
            self,
            msg_sudo.message_type,
            msg_sudo.subtype_id.id,
            pids=list(forwarded),
        )[self.id if self else 0]
        internal = msg_sudo.subtype_id.internal
        for forwarding_id, original_data in forwarded.items():
            data = forwarding_data.get(forwarding_id)
            if not data or data["active"] is False:
                continue
            # internal messages are not forwarded to external partners
            if internal and data["share"]:
                continue
            data["is_cc"] = original_data.get("is_cc", False)
            recipient_data.append(data)
        return recipient_data
