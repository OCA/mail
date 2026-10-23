# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.fields import Domain

from odoo.addons.mail.controllers.discuss.messaging_menu import (
    DiscussMessagingMenuController,
)


class GatewayMessagingMenuController(DiscussMessagingMenuController):
    """Gateway tab of the messaging menu (Discuss sidebar)."""

    def _get_menu_tab_domain(self, tab_id):
        if tab_id != "gateway":
            return super()._get_menu_tab_domain(tab_id)
        return Domain(
            [
                ("channel_type", "=", "gateway"),
                ("self_member_id.is_pinned", "=", True),
            ]
        )

    def _get_menu_tab_filter_domain(self, tab_id, filter_id):
        if tab_id == "gateway":
            if filter_id == "gateway_unread":
                return Domain("self_member_id.is_unread", "=", True)
            # One filter for each gateway: "gateway_<mail.gateway id>"
            gateway_id = filter_id.removeprefix("gateway_")
            if gateway_id.isdigit():
                return Domain("gateway_id", "=", int(gateway_id))
        return super()._get_menu_tab_filter_domain(tab_id, filter_id)
