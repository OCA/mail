# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

from odoo.addons.mail.tools.discuss import Store


class MailNotification(models.Model):
    _inherit = "mail.notification"

    gateway_channel_id = fields.Many2one("discuss.channel")
    notification_type = fields.Selection(
        selection_add=[("gateway", "Gateway")], ondelete={"gateway": "cascade"}
    )
    gateway_message_id = fields.Char(readonly=True)
    gateway_failure_reason = fields.Text(
        readonly=True,
        help="Failure reason. This is usually the exception thrown by the"
        " email server, stored to ease the debugging of mailing issues.",
    )
    gateway_type = fields.Selection(
        selection=lambda r: r.env["mail.gateway"]._fields["gateway_type"].selection
    )

    def _set_read_gateway(self):
        self.sudo().write({"is_read": True, "read_date": fields.Datetime.now()})

    def _to_store_defaults(self, target):
        return super()._to_store_defaults(target) + [
            "gateway_type",
            Store.One(
                "gateway_channel_id",
                [
                    "name",
                    Store.Attr("display_name", predicate=lambda p: not p.name),
                ],
            ),
            # Shown in the message notification popover instead of the generic
            # "Exception" (19.0 has no mail.resend.message wizard any more).
            Store.Attr(
                "gateway_failure_summary",
                lambda n: n._get_gateway_failure_summary(),
                predicate=lambda n: n.notification_type == "gateway",
            ),
        ]

    def _get_gateway_failure_summary(self, max_length=300):
        self.ensure_one()
        if not self.failure_reason or self.notification_status not in (
            "exception",
            "bounce",
        ):
            return False
        lines = [line.strip() for line in self.failure_reason.splitlines()]
        summary = " · ".join(line for line in lines if line)
        if len(summary) > max_length:
            summary = summary[: max_length - 1] + "…"
        return summary

    def send_gateway(self, auto_commit=False, raise_exception=False, parse_mode="HTML"):
        for record in self:
            # sudo: mail.gateway is readable only by administrators
            gateway = record.sudo().gateway_channel_id.gateway_id
            self.env[f"mail.gateway.{gateway.gateway_type}"]._send(
                gateway,
                record,
                auto_commit=auto_commit,
                raise_exception=raise_exception,
                parse_mode=parse_mode,
            )
            # notify user that we have a failure
            if record.failure_type == "unknown":
                record.mail_message_id._notify_message_notification_update()
