# Copyright 2026 Quartile (https://quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from lxml import etree

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user
from odoo.tools.misc import format_datetime
from odoo.tools.safe_eval import safe_eval


class TestMailMessageHistory(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})
        cls.user = new_test_user(
            cls.env,
            login="test-mail-message-history",
            groups="base.group_user",
        )

    def _flush_tracking(self):
        """Force the creation of the tracking messages."""
        self.env.flush_all()
        self.cr.flush()

    def _post_note(self, body):
        return self.partner.message_post(
            body=body, message_type="comment", subtype_xmlid="mail.mt_note"
        )

    def test_record_name_of_a_log(self):
        # Core leaves record_name empty on the messages it logs, which is what
        # the message history is mostly made of.
        log = self.partner._message_log(body="<p>A log</p>")
        self.assertEqual(log.record_name, self.partner.display_name)
        self.assertFalse(self.env["mail.message"].create({}).record_name)

    def test_record_name_of_a_user_notification(self):
        # The empty document name of a user notification drives the subject of
        # its notification email, so it is left untouched.
        notification = self.partner.message_notify(
            body="<p>A notification</p>", partner_ids=self.partner.ids
        )
        self.assertFalse(notification.record_name)

    def test_tracking_summary(self):
        blacklist = self.env["mail.blacklist"].create({"email": "old@example.org"})
        self._flush_tracking()
        blacklist.write({"email": "new@example.org", "active": False})
        self._flush_tracking()
        self.assertEqual(
            blacklist.message_ids.filtered("tracking_summary").tracking_summary,
            "Email Address: old@example.org → new@example.org | Active: Yes → No",
        )

    def test_tracking_summary_datetime(self):
        message = self._post_note("<p>A note</p>")
        self.env["mail.tracking.value"].create(
            {
                "field": self.env["ir.model.fields"]
                ._get("res.partner", "write_date")
                .id,
                "field_desc": "Last Updated on",
                "field_type": "datetime",
                "old_value_datetime": "2026-01-02 03:04:05",
                "new_value_datetime": "2026-01-02 04:05:06",
                "mail_message_id": message.id,
            }
        )
        self.assertEqual(
            message.tracking_summary,
            "Last Updated on: %s → %s"
            % (
                format_datetime(
                    self.env, fields.Datetime.to_datetime("2026-01-02 03:04:05")
                ),
                format_datetime(
                    self.env, fields.Datetime.to_datetime("2026-01-02 04:05:06")
                ),
            ),
        )

    def test_tracking_summary_as_internal_user(self):
        message = self._post_note("<p>A note</p>")
        self.env["mail.tracking.value"].create(
            {
                "field": self.env["ir.model.fields"]._get("res.partner", "name").id,
                "field_desc": "Name",
                "field_type": "char",
                "old_value_char": "Old Name",
                "new_value_char": "New Name",
                "mail_message_id": message.id,
            }
        )
        message_user = message.with_user(self.user)
        # tracking_value_ids itself is restricted to base.group_system, which is
        # why the summary is computed as sudo.
        with self.assertRaises(AccessError):
            message_user.read(["tracking_value_ids"])
        self.assertEqual(message_user.tracking_summary, "Name: Old Name → New Name")

    def test_action_view_mail_messages(self):
        action = self.partner.action_view_mail_messages()
        self.assertEqual(action["res_model"], "mail.message")
        self.assertEqual(
            action["domain"],
            [("model", "=", "res.partner"), ("res_id", "=", self.partner.id)],
        )
        self.assertFalse(action["context"])

    def test_menu_action(self):
        action = self.env.ref("mail_message_history.mail_message_action")
        # The menu opens on a bounded set of messages, as listing the messages
        # of every document is expensive.
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
            [field.get("name") for field in list_arch.xpath("//field")][:4],
            ["date", "preview", "tracking_summary", "subject"],
            "The message content must come right after the date.",
        )
        self.assertTrue(
            list_arch.xpath("//button[@name='action_open_document']"),
            "The list must offer to open the document of the message.",
        )
        self.assertTrue(list_arch.xpath("//field[@name='record_name']"))
        search_arch = etree.fromstring(views["views"]["search"]["arch"])
        self.assertTrue(search_arch.xpath("//filter[@name='filter_user_message']"))
        # The module fills record_name, so the document can be searched and
        # grouped on, which an unstored field would not allow.
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
        # The menu is a history browser, not a place to attach files to past
        # messages.
        modifiers = json.loads(attachment_fields[0].get("modifiers"))
        self.assertTrue(modifiers.get("readonly"))

    def test_standard_views_are_left_untouched(self):
        # The views of the menu are variants of the standard ones (primary
        # mode), so that the standard Messages list keeps its own columns.
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
