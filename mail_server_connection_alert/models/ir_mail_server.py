# Copyright 2026 CIT-Services
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from markupsafe import Markup

from odoo import Command, api, models

_logger = logging.getLogger(__name__)


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    def _format_failure_item(self, label, message, url=False):
        if url:
            bus_item = Markup(
                f'[{label}] <a href="{url}" class="alert-link '
                f'text-decoration-underline">{message}</a>'
            )
            list_item = Markup(f'<li><a href="{url}">{message}</a></li>')
        else:
            bus_item = f"[{label}] {message}"
            list_item = Markup(f"<li>{message}</li>")
        return bus_item, list_item

    @api.model
    def _process_reminders(self):
        failures = {
            "outgoing": {"web_notify_data": [], "channel_data": []},
            "incoming": {"web_notify_data": [], "channel_data": []},
        }

        base_url = self.get_base_url()

        active_outgoing = self.search([("active", "=", True)])
        if not active_outgoing:
            bus_item, list_item = self._format_failure_item(
                "Outgoing",
                "No active outgoing mail servers found in system settings.",
            )
            failures["outgoing"]["web_notify_data"].append(bus_item)
            failures["outgoing"]["channel_data"].append(list_item)
        else:
            for server in active_outgoing:
                try:
                    server.test_smtp_connection()
                except Exception as e:
                    _logger.warning(
                        "Outgoing mail server %s (ID: %s) connection failed: %s",
                        server.name,
                        server.id,
                        e,
                    )
                    bus_item, list_item = self._format_failure_item(
                        "Outgoing",
                        f"{server.name} (ID: {server.id}) is not working properly.",
                        url=f"{base_url}/odoo/{server._name}/{server.id}",
                    )
                    failures["outgoing"]["web_notify_data"].append(bus_item)
                    failures["outgoing"]["channel_data"].append(list_item)

        incoming_servers = self.env["fetchmail.server"].search(
            [
                ("active", "=", True),
                ("server_type", "!=", "local"),
                ("state", "=", "done"),
            ]
        )
        for inc_server in incoming_servers:
            connection = None
            try:
                connection = inc_server.connect()
            except Exception as e:
                _logger.warning(
                    "Incoming mail server %s (ID: %s) connection failed: %s",
                    inc_server.name,
                    inc_server.id,
                    e,
                )
                bus_item, list_item = self._format_failure_item(
                    "Incoming",
                    f"{inc_server.name} (ID: {inc_server.id}) is not working properly.",
                    url=f"{base_url}/odoo/{inc_server._name}/{inc_server.id}",
                )
                failures["incoming"]["web_notify_data"].append(bus_item)
                failures["incoming"]["channel_data"].append(list_item)
            finally:
                try:
                    if connection:
                        connection_type = inc_server.server_type
                        if connection_type == "imap":
                            connection.close()
                        elif connection_type == "pop":
                            connection.quit()
                except Exception as e:
                    _logger.debug("Failed to close incoming mail connection: %s", e)

        if (
            failures["outgoing"]["web_notify_data"]
            or failures["incoming"]["web_notify_data"]
        ):
            self._notify_system_admins(failures)

    def _notify_system_admins(self, failures):
        admin_group = self.env.ref("base.group_system")
        admin_users = admin_group.users
        if not admin_users:
            return
        admin_partners = admin_users.mapped("partner_id")
        odoobot_partner = self.env.ref("base.partner_root")
        all_members = admin_partners | odoobot_partner

        outgoing = failures.get("outgoing", {})
        incoming = failures.get("incoming", {})

        if outgoing.get("web_notify_data"):
            admin_users.sudo().notify_danger(
                title="⚠️ Outgoing Mail System Warning",
                message=Markup("<br/>").join(outgoing.get("web_notify_data")),
                sticky=True,
                html=True,
            )
        if incoming.get("web_notify_data"):
            admin_users.sudo().notify_danger(
                title="⚠️ Incoming Mail System Warning",
                message=Markup("<br/>").join(incoming.get("web_notify_data")),
                sticky=True,
                html=True,
            )

        channel = self.env.ref(
            "mail_server_connection_alert.channel_system_mail_alerts"
        ).sudo()

        channel.channel_partner_ids = [Command.link(pid) for pid in all_members.ids]

        html_sections = []
        if outgoing.get("channel_data"):
            html_sections.append(
                f"<p><b>Outgoing Mail Server(s):</b></p><ul>"
                f"{''.join(outgoing.get('channel_data'))}</ul>"
            )
        if incoming.get("channel_data"):
            prefix = "<br/>" if html_sections else ""
            html_sections.append(
                f"{prefix}<p><b>Incoming Mail Server(s):</b></p><ul>"
                f"{''.join(incoming.get('channel_data'))}</ul>"
            )

        formatted_body = Markup(
            "<h3>⚠️ Mail System Warning</h3><br/>" + "".join(html_sections)
        )

        channel.sudo().message_post(
            body=formatted_body,
            author_id=odoobot_partner.id,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            silent=True,
        )
