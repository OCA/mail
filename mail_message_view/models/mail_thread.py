# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo import _, api, models

BUTTON_MODELS_PARAM = "mail_message_view.button_models"


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        if view_type == "form":
            arch = self._add_mail_message_button(arch)
        return arch, view

    def action_view_mail_messages(self):
        self.ensure_one()
        # The action holds the views to use, so it is the single place defining
        # how the messages are listed.
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "mail_message_view.mail_message_action"
        )
        action["display_name"] = _("Messages of %s", self.display_name)
        action["domain"] = [("model", "=", self._name), ("res_id", "=", self.id)]
        # Show every message of the record, unlike the menu action which
        # defaults to the messages posted by users during the last months.
        action["context"] = {}
        return action

    @api.model
    def _add_mail_message_button(self, arch):
        """Add a stat button opening the messages of the record.

        The button is only added on the models listed in the system parameter
        ``mail_message_view.button_models``, as it does not make sense on every
        model inheriting mail.thread.
        """
        # get_param is cached and setting a parameter clears the caches, which
        # also invalidates the cached views (see ir.ui.view._get_view_cache).
        models_param = (
            self.env["ir.config_parameter"].sudo().get_param(BUTTON_MODELS_PARAM) or ""
        )
        if self._name not in [model.strip() for model in models_param.split(",")]:
            return arch
        if not arch.xpath("//div[contains(@class, 'oe_chatter')]"):
            # A model may have several form views, and a message history button
            # only makes sense on the ones showing the chatter.
            return arch
        button_boxes = arch.xpath("//div[@name='button_box']")
        if button_boxes:
            button_box = button_boxes[0]
        else:
            sheets = arch.xpath("//sheet")
            if not sheets:
                # Forms without a sheet are usually dialogs or inline views.
                return arch
            button_box = etree.Element(
                "div", {"class": "oe_button_box", "name": "button_box"}
            )
            sheets[0].insert(0, button_box)
        button = etree.SubElement(
            button_box,
            "button",
            {
                "name": "action_view_mail_messages",
                "type": "object",
                "class": "oe_stat_button",
                "icon": "fa-comments-o",
            },
        )
        # The view cache key includes the language, so the label can safely be
        # translated here (see ir.ui.view._get_view_cache_key).
        info = etree.SubElement(button, "div", {"class": "o_field_widget o_stat_info"})
        etree.SubElement(info, "span", {"class": "o_stat_text"}).text = _("Messages")
        return arch
