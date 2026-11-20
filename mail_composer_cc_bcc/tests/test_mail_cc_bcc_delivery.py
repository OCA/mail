# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged
from odoo.tools import email_normalize_all

from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.addons.mail.tests.common import MailCommon


@tagged("post_install", "-at_install")
class TestMailCcBccDelivery(MailCommon):
    """Every To, Cc and Bcc recipient gets exactly one email, sees only the
    To and Cc headers, and one bad recipient never blocks the others."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The documents are partners: on Odoo 18 MailCommon's employee cannot
        # post on them (on 19.0 it is a partner manager)
        cls.user_employee.groups_id += cls.env.ref("base.group_partner_manager")
        cls.env["res.lang"]._activate_lang("nl_NL")
        Partner = cls.env["res.partner"].with_context(mail_create_nosubscribe=True)
        cls.record = Partner.create({"name": "Document", "email": "doc@example.com"})
        # Names mimic production: Odoo sorts the copies on complete_name, so the
        # customer comes after the "Acme" colleagues.
        cls.customer = Partner.create(
            {
                "name": "Zenith Industries, Tom",
                "email": "tom@zenith.example.com",
                "lang": "en_US",
            }
        )
        cls.customer_upper = Partner.create(
            {"name": "Orbit, Oscar", "email": "Oscar.Olsen@Orbit.example.com"}
        )
        cls.cc_anna, cls.cc_anne = Partner.create(
            [
                {
                    "name": "Acme Trading N.V., Anna",
                    "email": "anna@acme.example.com",
                    "lang": "nl_NL",
                },
                {
                    "name": "Acme Trading N.V., Anne",
                    "email": "anne@acme.example.com",
                    "lang": "nl_NL",
                },
            ]
        )
        cls.cc_upper = Partner.create(
            {
                "name": "Acme Trading N.V., Diane",
                "email": "Diane.D@acme.example.com",
            }
        )
        cls.bcc_bob, cls.bcc_bea, cls.bcc_ben = Partner.create(
            [
                {
                    "name": "Acme Trading N.V., Bob",
                    "email": "bob@acme.example.com",
                },
                {
                    "name": "Acme Trading N.V., Bea",
                    "email": "bea@acme.example.com",
                },
                {
                    "name": "Acme Trading N.V., Ben",
                    "email": "Ben.Baker@acme.example.com",
                },
            ]
        )
        cls.no_email = Partner.create({"name": "Zonder E-mail"})
        cls.two_emails = Partner.create(
            {"name": "Duo", "email": "duo.one@example.com, duo.two@example.com"}
        )
        cls.follower_external = Partner.create(
            {"name": "Externe Volger", "email": "volger@example.com"}
        )

    # ------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------

    def _composer(self, to, cc=None, bcc=None, lang=None, **values):
        return (
            self.env["mail.compose.message"]
            .with_user(self.user_employee)
            .with_context(
                lang=lang or self.env.lang,
                default_model=self.record._name,
                default_res_ids=self.record.ids,
                default_composition_mode="comment",
            )
            .create(
                {
                    "subject": "Offerte",
                    "body": "<p>Hello</p>",
                    "partner_ids": [Command.set(to.ids)],
                    "partner_cc_ids": [Command.set(cc.ids if cc else [])],
                    "partner_bcc_ids": [Command.set(bcc.ids if bcc else [])],
                    **values,
                }
            )
        )

    def _send(self, to, cc=None, bcc=None, lang=None):
        composer = self._composer(to, cc=cc, bcc=bcc, lang=lang)
        with self.mock_mail_gateway():
            composer._action_send_mail()
        return self.record.message_ids[0]

    def _envelopes(self):
        return [[a.lower() for a in e["smtp_to_list"]] for e in self.emails]

    def _report(self, message):
        notifs = sorted(
            (n.res_partner_id.name, n.notification_status, n.failure_type or "")
            for n in message.notification_ids
        )
        sent = [(e["smtp_to_list"], e["msg_to"], e["msg_cc"]) for e in self.emails]
        return f"\nnotifications: {notifs}\nsent (envelope, To, Cc): {sent}"

    def _received(self, partner):
        """How many SMTP emails reached the partner (for each of its addresses)"""
        return [
            sum(email in envelope for envelope in self._envelopes())
            for email in email_normalize_all(partner.email)
        ]

    def _assert_each_received_once(self, message, partners):
        report = self._report(message)
        for partner in partners:
            self.assertEqual(
                self._received(partner),
                [1] * len(email_normalize_all(partner.email)),
                f"{partner.name} should receive exactly one email{report}",
            )
            notif = message.notification_ids.filtered(
                lambda n, p=partner: n.res_partner_id == p
            )
            self.assertEqual(
                notif.mapped("notification_status"),
                ["sent"],
                f"{partner.name} should have one sent notification{report}",
            )

    # ------------------------------------------------------------
    # A. CONFIRMED IN PRODUCTION
    # ------------------------------------------------------------

    def test_a1_to_with_uppercase_email(self):
        message = self._send(self.customer_upper)
        self._assert_each_received_once(message, self.customer_upper)

    def test_a1_cc_with_uppercase_email(self):
        message = self._send(self.customer, cc=self.cc_upper)
        self._assert_each_received_once(message, self.customer + self.cc_upper)

    def test_a1_bcc_with_uppercase_email(self):
        message = self._send(self.customer, bcc=self.bcc_ben)
        self._assert_each_received_once(message, self.customer + self.bcc_ben)

    def test_a2_cc_neither_doubled_nor_dropped(self):
        # The Cc-only copy is one too many: res.pop() then drops whoever comes
        # last, which can be the customer
        message = self._send(self.customer, cc=self.cc_anna + self.cc_anne)
        self._assert_each_received_once(
            message, self.customer + self.cc_anna + self.cc_anne
        )

    def test_a2_a3_customer_two_cc_three_bcc(self):
        bcc = self.bcc_bob + self.bcc_bea + self.bcc_ben
        message = self._send(self.customer, cc=self.cc_anna + self.cc_anne, bcc=bcc)
        self._assert_each_received_once(
            message, self.customer + self.cc_anna + self.cc_anne + bcc
        )

    def test_a3_multiple_bcc(self):
        bcc = self.bcc_bob + self.bcc_bea + self.bcc_ben
        message = self._send(self.customer, bcc=bcc)
        self._assert_each_received_once(message, self.customer + bcc)

    def test_a4_bcc_not_visible_to_other_recipients(self):
        bcc = self.bcc_bob + self.bcc_bea
        self._send(self.customer, cc=self.cc_anna, bcc=bcc)
        bcc_emails = bcc.mapped("email_normalized")
        report = self._report(self.record.message_ids[0])
        others = [
            e
            for e in self.emails
            if not set(bcc_emails) & {a.lower() for a in e["smtp_to_list"]}
        ]
        self.assertTrue(others, f"No email sent to To / Cc{report}")
        for email in others:
            source = email["message"].lower()
            for bcc_email in bcc_emails:
                self.assertNotIn(
                    bcc_email, source, f"Bcc leaked to {email['smtp_to_list']}{report}"
                )

    def test_a5_cc_once_with_different_langs(self):
        # Odoo creates one mail.mail per lang: the Cc must not get one per lang.
        # A Dutch sender to an English customer splits them.
        message = self._send(self.customer, cc=self.cc_anna, lang="nl_NL")
        self._assert_each_received_once(message, self.customer + self.cc_anna)
        report = self._report(message)
        for email in self.emails:
            self.assertIn(self.customer.email, email["msg_to"] or "", report)

    def test_a6_partner_without_email_does_not_block_others(self):
        message = self._send(self.customer + self.no_email, cc=self.cc_anna)
        self._assert_each_received_once(message, self.customer + self.cc_anna)
        notif = message.notification_ids.filtered(
            lambda n: n.res_partner_id == self.no_email
        )
        self.assertEqual(notif.notification_status, "exception", self._report(message))
        self.assertIn(
            notif.failure_type,
            ("mail_email_invalid", "mail_email_missing"),
            self._report(message),
        )

    # ------------------------------------------------------------
    # B. FOUND IN THE CODE
    # ------------------------------------------------------------

    def test_b3_internal_follower_not_in_customer_to_header(self):
        self.user_admin.notification_type = "email"
        self.record.message_subscribe(self.partner_admin.ids)
        message = self._send(self.customer, cc=self.cc_anna)
        report = self._report(message)
        customer_email = next(
            e for e in self.emails if self.customer.email in e["smtp_to_list"]
        )
        self.assertNotIn(
            self.partner_admin.email_normalized,
            (customer_email["msg_to"] or "").lower(),
            report,
        )
        self.assertNotIn(
            self.partner_admin.email_normalized,
            (customer_email["msg_cc"] or "").lower(),
            report,
        )

    def test_b5_cc_bcc_do_not_leak_to_a_followup_comment(self):
        # e.g. an automation posting on "quotation sent", in the same transaction
        RecordModel = type(self.record)
        origin = RecordModel._message_post_after_hook
        followups = []

        def _after_hook(record, message, msg_vals):
            res = origin(record, message, msg_vals)
            if not followups:
                followups.append(None)
                followups[0] = record.message_post(
                    body="Follow-up",
                    partner_ids=self.customer_upper.ids,
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment",
                )
            return res

        with patch.object(
            RecordModel,
            "_message_post_after_hook",
            autospec=True,
            side_effect=_after_hook,
        ):
            self._send(self.customer, cc=self.cc_anna, bcc=self.bcc_bob)
        report = self._report(followups[0])
        self.assertFalse(followups[0].recipient_cc_ids, report)
        self.assertFalse(followups[0].recipient_bcc_ids, report)
        self.assertFalse(
            followups[0].notification_ids.res_partner_id
            & (self.cc_anna + self.bcc_bob),
            report,
        )

    def _template(self, **values):
        return self.env["mail.template"].create(
            {
                "name": "Quotation",
                "model_id": self.env["ir.model"]._get_id(self.record._name),
                "subject": "Quotation {{ object.name }}",
                "body_html": "<p>Your quotation</p>",
                "partner_to": str(self.customer.id),
                # otherwise Odoo replaces partner_to and email_cc by the record
                "use_default_to": False,
                **values,
            }
        )

    def _template_composer(self, template):
        return (
            self.env["mail.compose.message"]
            .with_context(
                default_model=self.record._name,
                default_res_ids=self.record.ids,
                default_composition_mode="comment",
                default_template_id=template.id,
            )
            .create({})
        )

    def test_b6_switching_template_replaces_cc(self):
        template_eric = self._template(email_cc=self.cc_anna.email)
        template_erik = self._template(email_cc=self.cc_anne.email)
        composer = self._template_composer(template_eric)
        self.assertEqual(composer.partner_cc_ids, self.cc_anna)
        composer.template_id = template_erik
        self.assertEqual(composer.partner_cc_ids, self.cc_anne)

    # ------------------------------------------------------------
    # TEMPLATE NOTIFICATIONS (e.g. the order confirmation)
    # ------------------------------------------------------------

    def _post_with_template(self, template):
        with self.mock_mail_gateway():
            self.record.with_user(self.user_employee).with_context(
                mail_notify_force_send=True
            ).message_post_with_source(template, subtype_xmlid="mail.mt_comment")
        return self.record.message_ids[0]

    def test_t1_template_notification_uppercase_to(self):
        template = self._template(partner_to=str(self.customer_upper.id))
        message = self._post_with_template(template)
        self._assert_each_received_once(message, self.customer_upper)

    def test_t1_template_notification_cc_bcc(self):
        # e.g. colleagues in the Cc of the order confirmation template
        template = self._template(
            email_cc=self.cc_anna.email, email_bcc=self.bcc_bob.email
        )
        message = self._post_with_template(template)
        self._assert_each_received_once(
            message, self.customer + self.cc_anna + self.bcc_bob
        )
        report = self._report(message)
        for email in self.emails:
            self.assertIn(self.customer.email, email["msg_to"] or "", report)
            self.assertIn(self.cc_anna.email, email["msg_cc"] or "", report)
            if self.bcc_bob.email not in email["smtp_to_list"]:
                self.assertNotIn(self.bcc_bob.email, email["message"].lower(), report)

    # ------------------------------------------------------------
    # FOUND IN OCA/mail
    # ------------------------------------------------------------

    def test_n1_partner_both_in_to_and_cc(self):
        # OCA/mail#255: the To header used to end up empty
        message = self._send(self.customer, cc=self.customer + self.cc_anna)
        self._assert_each_received_once(message, self.customer + self.cc_anna)
        report = self._report(message)
        for email in self.emails:
            self.assertIn(self.customer.email, email["msg_to"] or "", report)

    def test_n2_queued_email_keeps_cc_bcc_behaviour(self):
        # OCA/mail#268: the queue cron and the Retry button send without the
        # composer context, the email must still go out the same way
        bcc = self.bcc_bob + self.bcc_bea
        composer = self._composer(
            self.customer, cc=self.cc_anna, bcc=bcc, force_send=False
        )
        with self.mock_mail_gateway():
            composer._action_send_mail()
        message = self.record.message_ids[0]
        mails = self._new_mails
        self.assertFalse(self.emails, "Nothing should be sent before the cron")
        with self.mock_mail_gateway():
            self.env["mail.mail"].process_email_queue(ids=mails.ids)
        self._assert_each_received_once(message, self.customer + self.cc_anna + bcc)
        report = self._report(message)
        for email in self.emails:
            self.assertIn(self.customer.email, email["msg_to"] or "", report)
            self.assertIn(self.cc_anna.email, email["msg_cc"] or "", report)
            if not set(bcc.mapped("email_normalized")) & set(email["smtp_to_list"]):
                for bcc_email in bcc.mapped("email_normalized"):
                    self.assertNotIn(bcc_email, email["message"].lower(), report)

    def test_n3_internal_bcc_not_in_to_header(self):
        # Odoo 18 has no Reply-All header (X-Msg-To-Add, merged into To on
        # 19.0): only check that no Bcc, internal one included, shows in To
        internal_bcc = self.partner_admin
        message = self._send(
            self.customer, cc=self.cc_anna, bcc=self.bcc_bob + internal_bcc
        )
        report = self._report(message)
        bcc_hidden = (self.bcc_bob + internal_bcc).mapped("email_normalized")
        for email in self.emails:
            for bcc_email in bcc_hidden:
                self.assertNotIn(bcc_email, (email["msg_to"] or "").lower(), report)
                self.assertNotIn(bcc_email, (email["msg_cc"] or "").lower(), report)

    def test_n4_reply_keeps_cc_bcc_of_parent_message(self):
        message = self._send(self.customer, cc=self.cc_anna, bcc=self.bcc_bob)
        reply = (
            self.env["mail.compose.message"]
            .with_user(self.user_employee)
            .with_context(
                default_model=self.record._name,
                default_res_ids=self.record.ids,
                default_composition_mode="comment",
                default_parent_id=message.id,
            )
            .create({"body": "<p>Reply</p>"})
        )
        self.assertEqual(reply.partner_cc_ids, self.cc_anna)
        self.assertEqual(reply.partner_bcc_ids, self.bcc_bob)

    # ------------------------------------------------------------
    # FULL COVERAGE
    # ------------------------------------------------------------

    def test_g1_internal_user_handling_in_odoo_gets_email_as_cc(self):
        self.assertEqual(self.user_admin.notification_type, "inbox")
        message = self._send(self.customer, cc=self.partner_admin)
        self._assert_each_received_once(message, self.customer + self.partner_admin)
        self.assertEqual(
            message.notification_ids.filtered(
                lambda n: n.res_partner_id == self.partner_admin
            ).notification_type,
            "email",
        )

    def test_g2_external_follower_receives_hidden(self):
        self.record.message_subscribe(self.follower_external.ids)
        message = self._send(self.customer, cc=self.cc_anna)
        self._assert_each_received_once(
            message, self.customer + self.cc_anna + self.follower_external
        )
        report = self._report(message)
        for email in self.emails:
            self.assertIn(self.customer.email, email["msg_to"] or "", report)
            headers = f"{email['msg_to']} {email['msg_cc']}".lower()
            self.assertNotIn(self.follower_external.email, headers, report)

    def test_g3_template_bcc_fills_composer_and_stays_hidden(self):
        template = self._template(
            email_cc=self.cc_anna.email, email_bcc=self.bcc_bob.email
        )
        composer = self._template_composer(template)
        self.assertEqual(composer.partner_ids, self.customer)
        self.assertEqual(composer.partner_cc_ids, self.cc_anna)
        self.assertEqual(composer.partner_bcc_ids, self.bcc_bob)
        with self.mock_mail_gateway():
            composer._action_send_mail()
        message = self.record.message_ids[0]
        self._assert_each_received_once(
            message, self.customer + self.cc_anna + self.bcc_bob
        )
        report = self._report(message)
        for email in self.emails:
            if self.bcc_bob.email not in email["smtp_to_list"]:
                self.assertNotIn(self.bcc_bob.email, email["message"].lower(), report)

    def test_g4_company_default_cc_bcc(self):
        self.env.company.write(
            {
                "default_partner_cc_ids": [Command.set(self.cc_anna.ids)],
                "default_partner_bcc_ids": [Command.set(self.bcc_bob.ids)],
            }
        )
        composer = (
            self.env["mail.compose.message"]
            .with_context(
                default_model=self.record._name,
                default_res_ids=self.record.ids,
                default_composition_mode="comment",
            )
            .create({"body": "<p>Hello</p>"})
        )
        self.assertEqual(composer.partner_cc_ids, self.cc_anna)
        self.assertEqual(composer.partner_bcc_ids, self.bcc_bob)
        # a template without Cc / Bcc falls back on the company defaults
        composer = self._template_composer(self._template())
        self.assertEqual(composer.partner_cc_ids, self.cc_anna)
        self.assertEqual(composer.partner_bcc_ids, self.bcc_bob)

    def test_g5_mass_mailing_ignores_cc_bcc(self):
        self.env.company.default_partner_cc_ids = self.cc_anna
        records = self.customer + self.customer_upper
        composer = (
            self.env["mail.compose.message"]
            .with_context(
                default_model="res.partner",
                default_res_ids=records.ids,
                default_composition_mode="mass_mail",
            )
            .create({"subject": "Newsletter", "body": "<p>Hello</p>"})
        )
        with self.mock_mail_gateway():
            composer._action_send_mail()
        sent = self._envelopes()
        self.assertEqual(
            sorted(sent),
            [["oscar.olsen@orbit.example.com"], ["tom@zenith.example.com"]],
        )
        self.assertFalse(self._new_mails.recipient_cc_ids, sent)
        self.assertFalse(any(e["msg_cc"] for e in self.emails), sent)

    def test_g6_no_x_odoo_bcc_header(self):
        # Older versions added it to every copy, disclosing the Bcc
        self._send(self.customer, bcc=self.bcc_bob + self.bcc_bea)
        for email in self.emails:
            self.assertNotIn(
                "x-odoo-bcc", email["message"].lower(), email["smtp_to_list"]
            )

    def test_g7_retry_after_smtp_failure(self):
        bcc = self.bcc_bob + self.bcc_bea
        composer = self._composer(self.customer, cc=self.cc_anna, bcc=bcc)
        with self.mock_mail_gateway():
            self.send_email_mocked.side_effect = MailDeliveryException("SMTP down")
            composer._action_send_mail()
            mails = self._new_mails
        message = self.record.message_ids[0]
        self.assertEqual(set(mails.mapped("state")), {"exception"})
        mails.action_retry()
        with self.mock_mail_gateway():
            self.env["mail.mail"].process_email_queue(ids=mails.ids)
        self._assert_each_received_once(message, self.customer + self.cc_anna + bcc)
        report = self._report(message)
        for email in self.emails:
            self.assertIn(self.customer.email, email["msg_to"] or "", report)
            self.assertIn(self.cc_anna.email, email["msg_cc"] or "", report)

    def test_g8_log_note_never_emails_cc_bcc(self):
        self.env.company.write(
            {
                "default_partner_cc_ids": [Command.set(self.cc_anna.ids)],
                "default_partner_bcc_ids": [Command.set(self.bcc_bob.ids)],
            }
        )
        composer = (
            self.env["mail.compose.message"]
            .with_user(self.user_employee)
            .with_context(
                default_model=self.record._name,
                default_res_ids=self.record.ids,
                default_composition_mode="comment",
                default_subtype_xmlid="mail.mt_note",
            )
            .create({"body": "<p>Internal note</p>"})
        )
        self.assertTrue(composer.subtype_is_log)
        with self.mock_mail_gateway():
            composer._action_send_mail()
        message = self.record.message_ids[0]
        self.assertFalse(self.emails, f"A note emails nobody: {self._envelopes()}")
        self.assertFalse(message.recipient_cc_ids)
        self.assertFalse(message.recipient_bcc_ids)

    def test_g9_message_without_cc_bcc_like_odoo(self):
        # Without Cc / Bcc the module stays out: Odoo's own per-recipient To
        # is kept
        message = self._send(self.customer + self.customer_upper)
        self._assert_each_received_once(message, self.customer + self.customer_upper)
        mail = self._new_mails
        self.assertFalse(mail.email_cc)
        self.assertFalse(mail.email_bcc)
        report = self._report(message)
        for email in self.emails:
            self.assertFalse(email["msg_cc"], report)
            for address in email["smtp_to_list"]:
                self.assertIn(address, (email["msg_to"] or "").lower(), report)

    def test_g10_partner_with_two_emails(self):
        message = self._send(self.customer + self.two_emails, cc=self.cc_anna)
        self._assert_each_received_once(
            message, self.customer + self.two_emails + self.cc_anna
        )

    def test_g11_only_cc_without_to(self):
        message = self._send(self.env["res.partner"], cc=self.cc_anna + self.cc_anne)
        self._assert_each_received_once(message, self.cc_anna + self.cc_anne)

    # ------------------------------------------------------------
    # FEATURES PROMISED BY THE README
    # ------------------------------------------------------------

    def test_f1_partner_both_in_to_and_bcc_stays_to(self):
        message = self._send(self.customer + self.cc_anna, bcc=self.cc_anna)
        self._assert_each_received_once(message, self.customer + self.cc_anna)
        report = self._report(message)
        # Nobody is left in Bcc: Odoo's own headers are kept. Odoo 18 shows
        # each recipient only itself in To (19.0 lists everyone), so Anna is
        # never hidden as a Bcc.
        anna_email = next(
            e for e in self.emails if self.cc_anna.email in e["smtp_to_list"]
        )
        self.assertIn(self.cc_anna.email, anna_email["msg_to"] or "", report)
        for email in self.emails:
            self.assertFalse(email["msg_cc"], report)

    def test_f2_headers_use_normalized_addresses(self):
        message = self._send(self.customer_upper, cc=self.cc_upper)
        report = self._report(message)
        for email in self.emails:
            self.assertIn("<oscar.olsen@orbit.example.com>", email["msg_to"], report)
            self.assertIn("<diane.d@acme.example.com>", email["msg_cc"], report)

    def test_f3_internal_user_handling_in_odoo_gets_email_as_bcc(self):
        self.assertEqual(self.user_admin.notification_type, "inbox")
        message = self._send(self.customer, bcc=self.partner_admin)
        self._assert_each_received_once(message, self.customer + self.partner_admin)

    def test_f4_cc_bcc_stored_on_message_and_email(self):
        composer = self._composer(self.customer, cc=self.cc_anna, bcc=self.bcc_bob)
        composer.force_send = False
        with self.mock_mail_gateway():
            composer._action_send_mail()
        message = self.record.message_ids[0]
        self.assertEqual(message.partner_ids, self.customer)
        self.assertEqual(message.recipient_cc_ids, self.cc_anna)
        self.assertEqual(message.recipient_bcc_ids, self.bcc_bob)
        for mail in self._new_mails:
            self.assertIn(self.cc_anna.email, mail.email_cc)
            self.assertIn(self.bcc_bob.email, mail.email_bcc)

    def test_f5_template_send_mail_like_odoo(self):
        # Automatic email: Odoo sends the template Cc, and knows no Bcc
        template = self._template(
            email_cc=self.cc_anna.email, email_bcc=self.bcc_bob.email
        )
        with self.mock_mail_gateway():
            template.send_mail(self.record.id, force_send=True)
        sent = self._envelopes()
        self.assertEqual(self._received(self.customer), [1], sent)
        self.assertEqual(self._received(self.cc_anna), [1], sent)
        self.assertEqual(self._received(self.bcc_bob), [0], sent)

    def test_f6_system_notification_gets_no_cc_bcc(self):
        # e.g. a tracking message posted in the same transaction as the send
        self._send(self.customer, cc=self.cc_anna, bcc=self.bcc_bob)
        with self.mock_mail_gateway():
            notification = self.record.with_context(
                mail_notify_force_send=True
            ).message_post(
                body="Stage changed",
                message_type="notification",
                partner_ids=self.customer_upper.ids,
                subtype_xmlid="mail.mt_comment",
            )
        self.assertFalse(notification.recipient_cc_ids)
        self.assertFalse(notification.recipient_bcc_ids)
        self.assertFalse(
            notification.notification_ids.res_partner_id & (self.cc_anna + self.bcc_bob)
        )
        self.assertEqual(self._received(self.cc_anna), [0], self._envelopes())
        self.assertEqual(self._received(self.bcc_bob), [0], self._envelopes())

    def test_f7_other_module_passes_cc_bcc_to_message_post(self):
        with self.mock_mail_gateway():
            message = self.record.with_context(
                mail_notify_force_send=True
            ).message_post(
                body="Invoice",
                partner_ids=self.customer.ids,
                recipient_cc_ids=self.cc_anna.ids,
                recipient_bcc_ids=self.bcc_bob.ids,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
        self._assert_each_received_once(
            message, self.customer + self.cc_anna + self.bcc_bob
        )
        report = self._report(message)
        for email in self.emails:
            self.assertIn(self.customer.email, email["msg_to"] or "", report)
            self.assertIn(self.cc_anna.email, email["msg_cc"] or "", report)
            if self.bcc_bob.email not in email["smtp_to_list"]:
                self.assertNotIn(self.bcc_bob.email, email["message"].lower(), report)

    def test_f8_unknown_template_cc_becomes_contact(self):
        template = self._template(email_cc="nieuw.contact@example.com")
        composer = self._template_composer(template)
        self.assertEqual(composer.partner_cc_ids.email, "nieuw.contact@example.com")
        with self.mock_mail_gateway():
            composer._action_send_mail()
        message = self.record.message_ids[0]
        self._assert_each_received_once(message, composer.partner_cc_ids)

    def test_f9_template_default_recipients_keeps_cc_bcc(self):
        # Odoo's order confirmation uses "Default Recipients", where Odoo itself
        # ignores the template Cc: the module still sends it
        self.env.company.default_partner_cc_ids = self.cc_anne
        template = self._template(
            use_default_to=True,
            partner_to=False,
            email_cc=self.cc_anna.email,
            email_bcc=self.bcc_bob.email,
        )
        message = self._post_with_template(template)
        self.assertEqual(message.recipient_cc_ids, self.cc_anna)
        self.assertEqual(message.recipient_bcc_ids, self.bcc_bob)
        self._assert_each_received_once(
            message, self.record + self.cc_anna + self.bcc_bob
        )
        # the company default Cc is only for emails a user writes
        self.assertEqual(self._received(self.cc_anne), [0], self._report(message))

    def test_f10_follower_in_cc_receives_once(self):
        # a colleague follows the order and is also put in Cc
        self.record.message_subscribe(self.cc_anne.ids)
        message = self._send(self.customer, cc=self.cc_anne)
        self._assert_each_received_once(message, self.customer + self.cc_anne)
        report = self._report(message)
        for email in self.emails:
            self.assertIn(self.cc_anne.email, email["msg_cc"] or "", report)

    # ------------------------------------------------------------
    # COMPOSER TO WITH A "DEFAULT RECIPIENTS" TEMPLATE
    # ------------------------------------------------------------

    def _default_recipients_composer(self, template, **values):
        return (
            self.env["mail.compose.message"]
            .with_user(self.user_employee)
            .with_context(
                default_model=self.record._name,
                default_res_ids=self.record.ids,
                default_composition_mode="comment",
                default_template_id=template.id,
            )
            .create(values)
        )

    def test_f11_default_recipients_template_keeps_default_to(self):
        # A user writing with a "Default Recipients" template (e.g. the
        # quotation "Send by email") gets Odoo's default recipients in To
        # (Odoo 18 has no suggested recipients in the composer)
        template = self._template(use_default_to=True, partner_to=False)
        composer = self._default_recipients_composer(template)
        self.assertEqual(composer.message_type, "comment")
        self.assertIn(self.record, composer.partner_ids)

    def test_f12_default_recipients_template_keeps_chosen_to(self):
        # Odoo does not recompute To from a "Default Recipients" template once
        # To holds partners: switching template keeps what the user chose
        template_a = self._template(use_default_to=True, partner_to=False)
        template_b = self._template(use_default_to=True, partner_to=False)
        composer = self._default_recipients_composer(template_a)
        composer.partner_ids = self.customer
        composer.template_id = template_b
        self.assertEqual(composer.partner_ids, self.customer)
