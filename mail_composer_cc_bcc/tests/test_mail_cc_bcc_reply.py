# Copyright 2026 Alejandro Abbas (skanndar)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests.common import TransactionCase


class TestMailCcBccReply(TransactionCase):
    """Replying to an existing message must reuse that message's Cc/Bcc.

    The composer's parent is a ``mail.message``, whose Cc/Bcc partner fields
    are ``recipient_cc_ids`` / ``recipient_bcc_ids`` (added by this module).
    The compute read ``parent_id.partner_cc_ids`` / ``partner_bcc_ids`` -
    names that only exist on the composer, never on ``mail.message`` - which
    raised ``AttributeError``. In the UI this is the "Reply" button of a
    ``mail.mail`` (Settings > Technical > Email > Emails), the only flow that
    builds a composer with a ``parent_id`` in ``comment`` mode.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.record = cls.env["res.partner"].create(
            {"name": "Document", "email": "document@example.com"}
        )
        cls.cc = cls.env["res.partner"].create(
            {"name": "Cc", "email": "cc@example.com"}
        )
        cls.bcc = cls.env["res.partner"].create(
            {"name": "Bcc", "email": "bcc@example.com"}
        )
        cls.parent = cls.record.message_post(
            body="parent",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        cls.parent.write(
            {
                "recipient_cc_ids": [Command.set(cls.cc.ids)],
                "recipient_bcc_ids": [Command.set(cls.bcc.ids)],
            }
        )

    def test_reply_reuses_parent_recipients(self):
        composer = (
            self.env["mail.compose.message"]
            .with_context(
                default_model=self.record._name,
                default_res_ids=self.record.ids,
                default_composition_mode="comment",
                default_parent_id=self.parent.id,
            )
            .create({"subject": "Re: parent", "body": "<p>reply</p>"})
        )
        self.assertEqual(composer.partner_cc_ids, self.cc)
        self.assertEqual(composer.partner_bcc_ids, self.bcc)
