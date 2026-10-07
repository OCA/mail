# Copyright 2026 Quartile (https://quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo import _, api, models
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval


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
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "mail_message_history.mail_message_action"
        )
        action["display_name"] = _("Messages of %s", self.display_name)
        action["domain"] = expression.AND(
            [
                safe_eval(action["domain"]),
                [("model", "=", self._name), ("res_id", "=", self.id)],
            ]
        )
        action["context"] = {}
        return action

    @api.model
    def _add_mail_message_button(self, arch):
        models_param = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("mail_message_history.button_models")
            or ""
        )
        if self._name not in [model.strip() for model in models_param.split(",")]:
            return arch
        if not arch.xpath("//div[contains(@class, 'oe_chatter')]"):
            return arch
        button_boxes = arch.xpath("//div[@name='button_box']")
        if button_boxes:
            button_box = button_boxes[0]
        else:
            sheets = arch.xpath("//sheet")
            if not sheets:
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
        info = etree.SubElement(button, "div", {"class": "o_field_widget o_stat_info"})
        etree.SubElement(info, "span", {"class": "o_stat_text"}).text = _("Messages")
        return arch
