# Copyright 2026
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""A bounce for ONE recipient must not mark the co-recipients as error.

mail.tracking.email tracks per SMTP send, so a bounce propagates to the
co-recipients' trackings (and recipients without a tracking show 'unknown').
tracking_status() must reconcile against the core mail.notification, which is
per recipient. Real case: Audióptica lead 153, msg 90749."""

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCoRecipientBounce(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        P = cls.env["res.partner"]
        cls.andrea = P.create({"name": "Andrea", "email": "andrea@example.com"})
        cls.gabriela = P.create({"name": "Gabriela", "email": "gabriela@example.com"})
        cls.eloisa = P.create({"name": "Eloisa", "email": "eloisa@example.com"})
        cls.subdir = P.create({"name": "Subdirector", "email": "subdir@example.com"})
        cls.recipients = cls.andrea | cls.gabriela | cls.eloisa | cls.subdir
        cls.msg = cls.env["mail.message"].create(
            {
                "subject": "Convocatoria",
                "message_type": "email",
                "subtype_id": cls.env.ref("mail.mt_comment").id,
                "model": "res.partner",
                "res_id": cls.andrea.id,
                "partner_ids": [(6, 0, cls.recipients.ids)],
            }
        )
        TE = cls.env["mail.tracking.email"].sudo()
        # One real bounce (andrea) + propagated soft-bounce on co-recipients;
        # gabriela has NO tracking at all.
        for p, state in [
            (cls.andrea, "soft-bounced"),
            (cls.eloisa, "soft-bounced"),
            (cls.subdir, "soft-bounced"),
        ]:
            TE.create(
                {
                    "name": "t",
                    "mail_message_id": cls.msg.id,
                    "partner_id": p.id,
                    "recipient": p.email,
                    "state": state,
                }
            )
        # Core mail.notification: per recipient, reliable.
        N = cls.env["mail.notification"].sudo()
        for p, st in [
            (cls.andrea, "bounce"),
            (cls.gabriela, "sent"),
            (cls.eloisa, "sent"),
            (cls.subdir, "sent"),
        ]:
            N.create(
                {
                    "mail_message_id": cls.msg.id,
                    "res_partner_id": p.id,
                    "notification_type": "email",
                    "notification_status": st,
                }
            )

    def _status_by_partner(self):
        return {e["partner_id"]: e["status"] for e in self.msg.tracking_status()}

    def test_only_real_bounce_shows_error(self):
        st = self._status_by_partner()
        self.assertEqual(st[self.andrea.id], "error", "the real bounce stays error")
        self.assertEqual(
            st[self.gabriela.id],
            "sent",
            "no-tracking co-recipient delivered by core must be 'sent', not 'unknown'",
        )
        self.assertEqual(
            st[self.eloisa.id],
            "sent",
            "co-recipient delivered by core must not inherit the bounce",
        )
        self.assertEqual(
            st[self.subdir.id],
            "sent",
            "co-recipient delivered by core must not inherit the bounce",
        )
