# Copyright 2026 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo.tests import TransactionCase

from odoo.addons.queue_job.tests.common import trap_jobs


class TestMailTemplateQueueJob(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Test customer", "email": "customer@example.com"}
        )
        cls.template = cls.env["mail.template"].create(
            {
                "name": "Test queued template",
                "model_id": cls.env.ref("base.model_res_partner").id,
                "subject": "Queued welcome {{ object.name }}",
                "body_html": "<p>Hello <t t-out='object.name'/></p>",
                "partner_to": "{{ object.id }}",
                "post_in_queue_job": True,
            }
        )
        cls.env["ir.model.data"].create(
            {
                "module": "mail_template_queue_job",
                "name": "test_queued_template",
                "model": "mail.template",
                "res_id": cls.template.id,
            }
        )

    def _template_messages(self, partner):
        return partner.message_ids.filtered(
            lambda m: m.subject == f"Queued welcome {partner.name}"
        )

    def test_post_delayed(self):
        with trap_jobs() as trap:
            messages = self.partner.message_post_with_source(
                self.template, subtype_xmlid="mail.mt_comment"
            )
            self.assertFalse(messages)
            trap.assert_jobs_count(1, only=self.partner._message_post_with_source_job)
            self.assertFalse(self._template_messages(self.partner))
            trap.perform_enqueued_jobs()
        message = self._template_messages(self.partner)
        self.assertEqual(len(message), 1)
        self.assertEqual(message.subtype_id, self.env.ref("mail.mt_comment"))
        self.assertIn(self.partner, message.partner_ids)

    def test_post_delayed_one_job_per_record(self):
        partners = self.partner + self.partner.copy({"name": "Other customer"})
        with trap_jobs() as trap:
            partners.message_post_with_source(self.template)
            trap.assert_jobs_count(2)
            trap.perform_enqueued_jobs()
        for partner in partners:
            self.assertEqual(len(self._template_messages(partner)), 1)

    def test_post_delayed_from_xmlid(self):
        with trap_jobs() as trap:
            self.partner.message_post_with_source(
                "mail_template_queue_job.test_queued_template"
            )
            trap.assert_jobs_count(1)
            trap.perform_enqueued_jobs()
        self.assertEqual(len(self._template_messages(self.partner)), 1)

    def test_post_not_delayed_template_disabled(self):
        self.template.post_in_queue_job = False
        with trap_jobs() as trap:
            messages = self.partner.message_post_with_source(self.template)
            trap.assert_jobs_count(0)
        self.assertEqual(messages, self._template_messages(self.partner))
        self.assertEqual(len(messages), 1)

    def test_post_not_delayed_no_delay_context(self):
        with trap_jobs() as trap:
            self.partner.with_context(
                queue_job__no_delay=True
            ).message_post_with_source(self.template)
            trap.assert_jobs_count(0)
        self.assertEqual(len(self._template_messages(self.partner)), 1)

    def test_post_view_not_delayed(self):
        with trap_jobs() as trap:
            messages = self.partner.message_post_with_source(
                "mail.message_origin_link",
                render_values={"self": self.partner, "origin": self.partner},
            )
            trap.assert_jobs_count(0)
        self.assertEqual(len(messages), 1)

    def test_post_delayed_record_deleted(self):
        partner = self.partner.copy({"name": "Deleted customer"})
        with trap_jobs() as trap:
            partner.message_post_with_source(self.template)
            partner.unlink()
            trap.perform_enqueued_jobs()
        self.assertFalse(
            self.env["mail.message"].search(
                [("subject", "=", "Queued welcome Deleted customer")]
            )
        )
