# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests.common import TransactionCase, new_test_user
from odoo.tools.safe_eval import safe_eval

from ..hooks import post_init_hook


class TestMailMessageHistory(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})

    def _flush_tracking(self):
        self.env.flush_all()
        self.cr.flush()

    def _post_note(self, body):
        return self.partner.message_post(
            body=body, message_type="comment", subtype_xmlid="mail.mt_note"
        )

    def test_record_name_of_a_log(self):
        log = self.partner._message_log(body="<p>A log</p>")
        self.assertEqual(log.record_name, self.partner.display_name)
        self.assertFalse(self.partner._message_log(body="").record_name)
        self.assertFalse(self.env["mail.message"].create({}).record_name)
        # Mass mail copies pass record_name as False too, to avoid browsing records.
        mass_mail_copy = self.env["mail.message"].create(
            {
                "model": "res.partner",
                "res_id": self.partner.id,
                "body": "<p>A copy</p>",
                "message_type": "comment",
                "record_name": False,
            }
        )
        self.assertFalse(mass_mail_copy.record_name)

    def test_model_description(self):
        log = self.partner._message_log(body="<p>A log</p>")
        self.assertEqual(log.model_description, "Contact")
        user = new_test_user(self.env, login="history_user", groups="base.group_user")
        self.assertIn(
            log,
            self.env["mail.message"]
            .with_user(user)
            .search([("model_description", "ilike", "contact")]),
        )

    def test_post_init_hook(self):
        log = self.partner._message_log(body="<p>A log</p>")
        empty_log = self.partner._message_log(body="")
        notification = self.partner.message_notify(
            body="<p>A notification</p>", partner_ids=self.partner.ids
        )
        messages = log | empty_log | notification
        self.env.flush_all()
        self.cr.execute(
            "UPDATE mail_message SET record_name = NULL WHERE id IN %s",
            (tuple(messages.ids),),
        )
        messages.invalidate_recordset(["record_name"])
        post_init_hook(self.cr, self.registry)
        self.assertEqual(log.record_name, self.partner.display_name)
        self.assertFalse(empty_log.record_name)
        self.assertFalse(notification.record_name)

    def test_menu_action_leaves_tracking_out(self):
        blacklist = self.env["mail.blacklist"].create({"email": "old@example.org"})
        self._flush_tracking()
        blacklist.write({"email": "new@example.org"})
        self._flush_tracking()
        tracking = blacklist.sudo().message_ids.filtered("tracking_value_ids")
        self.assertTrue(tracking)
        log = self.partner._message_log(body="<p>A log</p>")
        attachment_only = self.partner.message_post(
            body="", attachments=[("file.txt", b"content")]
        )
        action = self.env.ref("mail_message_history.mail_message_action")
        messages = self.env["mail.message"].search(safe_eval(action.domain))
        self.assertNotIn(tracking, messages)
        self.assertIn(log, messages)
        self.assertIn(attachment_only, messages)

    def test_action_view_mail_messages(self):
        action = self.partner.action_view_mail_messages()
        self.assertEqual(action["res_model"], "mail.message")
        self.assertFalse(action["context"])
        note = self._post_note("<p>A note</p>")
        empty_log = self.partner._message_log(body="")
        other_note = (
            self.env["res.partner"]
            .create({"name": "Other"})
            .message_post(body="<p>Another note</p>")
        )
        messages = self.env["mail.message"].search(action["domain"])
        self.assertIn(note, messages)
        self.assertNotIn(empty_log, messages)
        self.assertNotIn(other_note, messages)

    def test_menu_action(self):
        action = self.env.ref("mail_message_history.mail_message_action")
        note = self._post_note("<p>A note</p>")
        without_document = self.env["mail.message"].create({})
        notification = self.partner.message_notify(
            body="<p>A notification</p>", partner_ids=self.partner.ids
        )
        messages = self.env["mail.message"].search(safe_eval(action.domain))
        self.assertIn(note, messages)
        self.assertNotIn(without_document, messages)
        self.assertNotIn(notification, messages)

    def test_group_by_hidden_from_non_admins(self):
        search_view = self.env.ref("mail_message_history.mail_message_view_search")

        def group_bys(env):
            views = env["mail.message"].get_views([(search_view.id, "search")])
            arch = etree.fromstring(views["views"]["search"]["arch"])
            return arch.xpath("//filter[contains(@context, 'group_by')]")

        user = new_test_user(self.env, login="history_user", groups="base.group_user")
        self.assertTrue(group_bys(self.env))
        self.assertFalse(group_bys(self.env(user=user)))

    def test_standard_views_are_left_untouched(self):
        standard = self.env["mail.message"].get_views(
            [(False, "list"), (False, "search")]
        )
        list_arch = etree.fromstring(standard["views"]["list"]["arch"])
        self.assertEqual(
            [field.get("name") for field in list_arch.xpath("//field")],
            ["date", "subject", "author_id", "model", "res_id"],
        )
        search_arch = etree.fromstring(standard["views"]["search"]["arch"])
        self.assertFalse(search_arch.xpath("//filter[@name='filter_user_message']"))

    def test_user_messages_leave_mass_mails_out(self):
        self.partner.email = "partner@example.org"
        self.env["mail.compose.message"].with_context(
            default_composition_mode="mass_mail",
            default_model="res.partner",
            active_ids=self.partner.ids,
        ).create(
            {"subject": "A mass mail", "body": "<p>A mass mail</p>"}
        )._action_send_mail()
        mass_mail_copy = self.partner.message_ids.filtered(
            lambda message: message.subject == "A mass mail"
        )
        self.assertTrue(mass_mail_copy)
        note = self._post_note("<p>A note</p>")
        search_view = self.env.ref("mail_message_history.mail_message_view_search")
        user_filter = etree.fromstring(search_view.arch).xpath(
            "//filter[@name='filter_user_message']"
        )[0]
        messages = self.env["mail.message"].search(
            safe_eval(user_filter.get("domain")) + [("res_id", "=", self.partner.id)]
        )
        self.assertIn(note, messages)
        self.assertNotIn(mass_mail_copy, messages)

    def test_smart_button(self):
        def has_button():
            arch = self.env["res.partner"].get_views([(False, "form")])["views"][
                "form"
            ]["arch"]
            return bool(
                etree.fromstring(arch).xpath(
                    "//div[@name='button_box']"
                    "/button[@name='action_view_mail_messages']"
                )
            )

        self.assertFalse(has_button())
        self.env["ir.config_parameter"].sudo().set_param(
            "mail_message_history.button_models", "sale.order, res.partner"
        )
        self.assertTrue(has_button())
