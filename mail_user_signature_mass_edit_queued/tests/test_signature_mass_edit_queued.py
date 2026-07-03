# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, new_test_user, tagged

from odoo.addons.queue_job.tests.common import trap_jobs


@tagged("post_install", "-at_install")
class TestSignatureMassEditQueued(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create(
            {"name": "Queued Signature Company"}
        )
        cls.user = new_test_user(
            cls.env,
            login="queued_signature_user",
            groups="base.group_user",
            context={"no_reset_password": True},
            name="Queued Signature User",
            company_id=cls.company.id,
            email="queued_signature_user@example.com",
        )
        cls.other_user = new_test_user(
            cls.env,
            login="other_queued_signature_user",
            groups="base.group_user",
            context={"no_reset_password": True},
            name="Other Queued Signature User",
            company_id=cls.company.id,
            email="other_queued_signature_user@example.com",
        )

    def test_confirm_enqueues_one_signature_job_per_user_and_done_job(self):
        mass_edit = self.env["signature.mass.edit"].create(
            {
                "company_id": self.company.id,
                "run_in_queue_job": True,
                "signature": "<p>{{ object.name }}</p>",
            }
        )

        with trap_jobs() as trap:
            mass_edit.action_confirm()

        self.assertEqual(mass_edit.state, "in_progress")
        trap.assert_jobs_count(3)
        for user in self.user | self.other_user:
            trap.assert_enqueued_job(
                mass_edit._queued_process_user_signature,
                args=(user.id,),
                properties={
                    "description": f"User signature mass edit - {user.display_name}"
                },
            )
        trap.assert_enqueued_job(
            mass_edit._queued_mark_signature_mass_edit_done,
            args=(2,),
            properties={
                "description": (
                    f"Mark user signature mass edit done - {mass_edit.display_name}"
                )
            },
        )
        jobs_by_call = list(zip(trap.calls, trap.enqueued_jobs, strict=True))
        user_jobs = {
            job
            for call, job in jobs_by_call
            if call.method.__func__ == mass_edit._queued_process_user_signature.__func__
        }
        done_jobs = [
            job
            for call, job in jobs_by_call
            if call.method.__func__
            == mass_edit._queued_mark_signature_mass_edit_done.__func__
        ]
        self.assertEqual(len(user_jobs), 2)
        self.assertEqual(len(done_jobs), 1)
        done_job = done_jobs[0]
        self.assertEqual(done_job.depends_on, user_jobs)
        self.assertTrue(done_job.graph_uuid)
        self.assertTrue(all(job.graph_uuid == done_job.graph_uuid for job in user_jobs))
        self.assertTrue(all(done_job in job.reverse_depends_on for job in user_jobs))

    def test_user_jobs_process_signature_mass_edit(self):
        mass_edit = self.env["signature.mass.edit"].create(
            {
                "company_id": self.company.id,
                "run_in_queue_job": True,
                "signature": "<p>{{ object.name }}</p>",
            }
        )

        with trap_jobs() as trap:
            mass_edit.action_confirm()
            trap.perform_enqueued_jobs()

        self.assertEqual(mass_edit.state, "done")
        self.assertEqual(mass_edit.processed_user_count, 2)
        self.assertEqual(self.user.signature, "<p>Queued Signature User</p>")
        self.assertEqual(
            self.other_user.signature,
            "<p>Other Queued Signature User</p>",
        )

    def test_confirm_processes_synchronously_by_default(self):
        mass_edit = self.env["signature.mass.edit"].create(
            {
                "company_id": self.company.id,
                "signature": "<p>{{ object.name }}</p>",
            }
        )

        with trap_jobs() as trap:
            mass_edit.action_confirm()

        trap.assert_jobs_count(0)
        self.assertFalse(mass_edit.run_in_queue_job)
        self.assertEqual(mass_edit.state, "done")
        self.assertEqual(mass_edit.processed_user_count, 2)
        self.assertEqual(self.user.signature, "<p>Queued Signature User</p>")
