# Copyright 2026 Quartile (https://quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from lxml import etree

from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval


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
        self.assertFalse(self.env["mail.message"].create({}).record_name)

    def test_record_name_of_a_user_notification(self):
        # Its empty record_name drives the subject of the notification email.
        notification = self.partner.message_notify(
            body="<p>A notification</p>", partner_ids=self.partner.ids
        )
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
        self.assertIn("search_default_filter_user_message", action.context)
        self.assertIn("search_default_filter_last_3_months", action.context)
        note = self._post_note("<p>A note</p>")
        without_document = self.env["mail.message"].create({})
        messages = self.env["mail.message"].search(safe_eval(action.domain))
        self.assertIn(note, messages)
        self.assertNotIn(without_document, messages)

    def test_message_history_views(self):
        action = self.env.ref("mail_message_history.mail_message_action")
        views = self.env["mail.message"].get_views(
            [
                (view.view_id.id, "list" if view.view_mode == "tree" else "form")
                for view in action.view_ids
            ]
            + [(action.search_view_id.id, "search")]
        )
        list_arch = etree.fromstring(views["views"]["list"]["arch"])
        self.assertEqual(
            [field.get("name") for field in list_arch.xpath("//field")][:3],
            ["date", "preview", "subject"],
            "The message content must come right after the date.",
        )
        self.assertTrue(
            list_arch.xpath("//button[@name='action_open_document']"),
            "The list must offer to open the document of the message.",
        )
        self.assertTrue(list_arch.xpath("//field[@name='record_name']"))
        search_arch = etree.fromstring(views["views"]["search"]["arch"])
        self.assertTrue(search_arch.xpath("//filter[@name='filter_user_message']"))
        self.assertTrue(search_arch.xpath("//field[@name='record_name']"))
        self.assertTrue(
            search_arch.xpath("//filter[@context[contains(., 'record_name')]]")
        )

    def test_message_history_form_shows_attachments(self):
        action = self.env.ref("mail_message_history.mail_message_action")
        form_view = next(view for view in action.view_ids if view.view_mode == "form")
        views = self.env["mail.message"].get_views([(form_view.view_id.id, "form")])
        form_arch = etree.fromstring(views["views"]["form"]["arch"])
        attachment_fields = form_arch.xpath("//field[@name='attachment_ids']")
        self.assertTrue(attachment_fields)
        self.assertEqual(attachment_fields[0].get("widget"), "many2many_binary")
        modifiers = json.loads(attachment_fields[0].get("modifiers"))
        self.assertTrue(modifiers.get("readonly"))

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
