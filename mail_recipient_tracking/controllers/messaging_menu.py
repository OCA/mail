# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo.fields import Domain

from odoo.addons.mail.controllers.messaging_menu import MessagingMenuController


class MailTrackingMessagingMenuController(MessagingMenuController):
    def _get_menu_tab_domain(self, tab_id):
        """Failed messages of the current user, shown in the messaging menu"""
        if tab_id == "failed":
            return Domain("is_failed_message", "=", True)
        return super()._get_menu_tab_domain(tab_id)
