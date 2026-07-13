# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from collections import Counter

from odoo import Command
from odoo.tests.common import TransactionCase
from odoo.tools import email_normalize, email_split

from odoo.addons.mail.tests.common import MailCase


class TestMailCcBccRecipients(TransactionCase, MailCase):
    """Sending from the composer to To, Cc and Bcc recipients must always give:

    * exactly one email per recipient,
    * the same To and Cc headers on every email,
    * a Bcc header on the Bcc recipients' emails only.

    Odoo may split the notification into one mail.mail per lang to render the
    layout in each lang. That is fine, but must not change any of the above:
    each recipient still belongs to exactly one mail.mail.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for code in ("fr_FR", "de_DE", "es_ES"):
            cls.env["res.lang"]._activate_lang(code)
        cls.record = cls.env["res.partner"].create(
            {"name": "Document", "email": "document@example.com"}
        )
        # us1 belongs to both lists, hence 7 partners for 2 lists of 4
        cls.us1 = cls._create_partner("us1", "en_US")
        cls.us2 = cls._create_partner("us2", "en_US")
        cls.us3 = cls._create_partner("us3", "en_US")
        cls.us4 = cls._create_partner("us4", "en_US")
        cls.fr = cls._create_partner("fr", "fr_FR")
        cls.de = cls._create_partner("de", "de_DE")
        cls.es = cls._create_partner("es", "es_ES")

        cls.partners_same_lang = cls.us1 + cls.us2 + cls.us3 + cls.us4
        cls.partners_different_langs = cls.us1 + cls.fr + cls.de + cls.es

    # ------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------

    @classmethod
    def _create_partner(cls, prefix, lang):
        return cls.env["res.partner"].create(
            {
                "name": prefix.upper(),
                "email": f"{prefix.lower()}@example.com",
                "lang": lang,
            }
        )

    def _send(
        self, subject, partners_to, partners_cc, partners_bcc, mail_unlink_sent=False
    ):
        """Send one composer message, any number of To / Cc / Bcc partners"""
        composer = (
            self.env["mail.compose.message"]
            .with_context(
                default_model=self.record._name,
                default_res_ids=self.record.ids,
                default_composition_mode="comment",
                mail_notify_force_send=True,
            )
            .create(
                {
                    "subject": subject,
                    "body": "<p>Hello</p>",
                    "partner_ids": [Command.set(partners_to.ids)],
                    "partner_cc_ids": [Command.set(partners_cc.ids)],
                    "partner_bcc_ids": [Command.set(partners_bcc.ids)],
                }
            )
        )
        with self.mock_mail_gateway(mail_unlink_sent=mail_unlink_sent):
            composer._action_send_mail()
        return self.record.message_ids.filtered(lambda m: m.subject == subject)[:1]

    def _send_from_followers(
        self, subject, partners_to, partners_cc, partners_bcc, mail_unlink_sent=False
    ):
        """Send with no explicit To: the recipients are followers of the record"""
        self.record.message_subscribe(partner_ids=partners_to.ids)
        composer = (
            self.env["mail.compose.message"]
            .with_context(
                default_model=self.record._name,
                default_res_ids=self.record.ids,
                default_composition_mode="comment",
                mail_notify_force_send=True,
            )
            .create(
                {
                    "subject": subject,
                    "body": "<p>Hello</p>",
                    "partner_cc_ids": [Command.set(partners_cc.ids)],
                    "partner_bcc_ids": [Command.set(partners_bcc.ids)],
                }
            )
        )
        with self.mock_mail_gateway(mail_unlink_sent=mail_unlink_sent):
            composer._action_send_mail()
        return self.record.message_ids.filtered(lambda m: m.subject == subject)[:1]

    def _assert_emails_defined(self):
        assert hasattr(
            self, "emails"
        ), "self.emails undefined. Did you use _send method ?"
        assert self.emails, "No email was sent"

    def _envelope_recipients(self):
        """Who each sent email is actually for (RCPT TO), one entry per email"""
        # NOTE: `To` != `RCPT TO`
        self._assert_emails_defined()
        return [addr for email in self.emails for addr in email["smtp_to_list"]]

    def _assert_one_email_per_recipient(self, partners):
        expected = Counter(partners.mapped("email"))
        received = Counter(self._envelope_recipients())
        if received == expected:
            return
        report = ["Each recipient must get exactly 1 email:"]
        for address in sorted(set(expected) | set(received)):
            got = received.get(address, 0)
            wanted = expected.get(address, 0)
            flag = "  <-- WRONG" if got != wanted else ""
            report.append(f"    {address}: got {got}, expected {wanted}{flag}")
        report.append(
            f"  total sent: {sum(received.values())}, expected {len(partners)}"
        )
        self.fail("\n".join(report))

    def _assert_each_recipient_in_one_mail(self, message, partners):
        """Whatever the lang split, a recipient belongs to a single mail.mail"""
        received = Counter(
            partner.email for mail in message.mail_ids for partner in mail.recipient_ids
        )
        expected = Counter(partners.mapped("email"))
        if received == expected:
            return
        report = ["Each recipient must belong to exactly 1 mail.mail:"]
        for mail in message.mail_ids:
            report.append(f"    mail.mail: {mail.recipient_ids.mapped('email')}")
        for address in sorted(set(expected) | set(received)):
            report.append(
                f"    {address}: in {received.get(address, 0)} mail.mail, "
                f"expected {expected.get(address, 0)}"
            )
        self.fail("\n".join(report))

    def _assert_same_to_cc_headers(self, partners_to, partners_cc):
        self._assert_emails_defined()
        # To is built from a list and Cc from a joined string, and the partners
        # come out in no guaranteed order: compare addresses, not text.
        for header, expected in (("msg_to", partners_to), ("msg_cc", partners_cc)):
            values = {
                tuple(
                    sorted(email_normalize(a) for a in email_split(email[header] or ""))
                )
                for email in self.emails
            }
            self.assertEqual(
                len(values),
                1,
                f"Every email must show the same {header}, got {sorted(values)}",
            )
            self.assertEqual(sorted(values.pop()), sorted(expected.mapped("email")))

    def _assert_bcc_header_on_bcc_emails_only(self, partners_bcc):
        values = [(mail.get("headers") or {}).get("Bcc") for mail in self._mails]
        found = sorted(email_normalize(value) for value in values if value)
        self.assertEqual(
            found,
            sorted(partners_bcc.mapped("email")),
            "Only the Bcc recipients' emails carry a Bcc header, one each",
        )

    def _assert_headers(self, partners_to, partners_cc, partners_bcc):
        """Assertions on the sent emails only, no mail.mail needed"""
        self._assert_one_email_per_recipient(partners_to + partners_cc + partners_bcc)
        self._assert_same_to_cc_headers(partners_to, partners_cc)
        self._assert_bcc_header_on_bcc_emails_only(partners_bcc)

    def _assert_mails(self, message, partners_to, partners_cc, partners_bcc):
        self._assert_each_recipient_in_one_mail(
            message, partners_to + partners_cc + partners_bcc
        )
        self._assert_one_email_per_recipient(partners_to + partners_cc + partners_bcc)
        self._assert_same_to_cc_headers(partners_to, partners_cc)
        self._assert_bcc_header_on_bcc_emails_only(partners_bcc)

    # ------------------------------------------------------------
    # TESTS
    # ------------------------------------------------------------

    def test_same_lang(self):
        """4 recipients sharing one lang: a single mail.mail, 4 emails"""
        partners_to, cc_1, cc_2, partners_bcc = self.partners_same_lang
        partners_cc = cc_1 + cc_2
        message = self._send("same-lang", partners_to, partners_cc, partners_bcc)

        self.assertEqual(len(message.mail_ids), 1, "One lang means one mail.mail")
        self._assert_mails(message, partners_to, partners_cc, partners_bcc)

    def test_several_to_in_different_langs(self):
        """Two To in two langs still see each other in their To header"""
        partners_to = self.us1 + self.fr
        partners_cc = self.de
        partners_bcc = self.es
        message = self._send("many-to", partners_to, partners_cc, partners_bcc)

        self.assertEqual(len(message.mail_ids), 4, "One mail.mail per lang")
        self._assert_mails(message, partners_to, partners_cc, partners_bcc)

    def test_different_langs(self):
        """4 recipients, 4 langs: the split may happen, the emails must not change"""
        partners_to, cc_1, cc_2, partners_bcc = self.partners_different_langs
        partners_cc = cc_1 + cc_2
        message = self._send("different-langs", partners_to, partners_cc, partners_bcc)

        self._assert_mails(message, partners_to, partners_cc, partners_bcc)

    def test_followers_are_to_recipients(self):
        """Followers get the email, though they never reach partner_ids"""
        partners_to = self.us1 + self.fr
        message = self._send_from_followers("followers", partners_to, self.de, self.es)

        self.assertFalse(
            message.partner_ids, "Followers are not added to partner_ids by Odoo"
        )
        self._assert_mails(message, partners_to, self.de, self.es)

    def test_to_header_survives_sent_mails_being_unlinked(self):
        """Sent mails are unlinked: the last one must still show every To

        mail_unlink_sent is what production does, MailCase disables it.
        """
        partners_to, cc_1, cc_2, partners_bcc = self.partners_different_langs
        partners_cc = cc_1 + cc_2
        self._send(
            "unlinked",
            partners_to,
            partners_cc,
            partners_bcc,
            mail_unlink_sent=True,
        )
        # no _assert_mails here: the mail.mail are gone, only the emails remain
        self._assert_headers(partners_to, partners_cc, partners_bcc)

    def test_no_recipient_left_refuses_to_send(self):
        """Running out of recipients must raise, never fall back to To+Cc+Bcc

        The fallback would send to everyone at once and disclose the Bcc.
        """
        mail_server = self.env["ir.mail_server"]
        message = mail_server.build_email(
            email_from="sender@example.com",
            email_to=[self.us1.email],
            subject="no-recipient-left",
            body="<p>Hello</p>",
            email_cc=self.de.email,
            email_bcc=self.es.email,
        )
        server = mail_server.with_context(is_from_composer=True, recipients=[])
        with self.assertRaises(ValueError):
            server._prepare_email_message(message, None)
