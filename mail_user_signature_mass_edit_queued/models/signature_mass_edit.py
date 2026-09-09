# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from odoo.addons.queue_job.delay import chain, group


class SignatureMassEdit(models.Model):
    _inherit = "signature.mass.edit"

    state = fields.Selection(
        selection_add=[("in_progress", "In Progress"), ("done",)],
        ondelete={"in_progress": "set default"},
    )
    run_in_queue_job = fields.Boolean(string="Run in Queue Job")

    def action_confirm(self):
        sync_records = self.filtered(lambda record: not record.run_in_queue_job)
        if sync_records:
            super(SignatureMassEdit, sync_records).action_confirm()
        for record in self - sync_records:
            record._check_can_confirm()
            users = record._get_target_users()
            record.write({"processed_user_count": 0, "state": "in_progress"})
            if not users:
                record._mark_signature_mass_edit_done(0)
                continue
            record._delay_process_user_signatures(users)
        return True

    def _delay_process_user_signatures(self, users):
        self.ensure_one()
        user_jobs = group(
            *(
                self.delayable()
                .set(
                    description=self.env._(
                        "User signature mass edit - %(user)s",
                        user=user.display_name,
                    )
                )
                ._queued_process_user_signature(user.id)
                for user in users
            )
        )
        done_job = (
            self.delayable()
            .set(
                description=self.env._(
                    "Mark user signature mass edit done - %(name)s",
                    name=self.display_name,
                )
            )
            ._queued_mark_signature_mass_edit_done(len(users))
        )
        chain(user_jobs, done_job).delay()

    def _queued_process_user_signature(self, user_id):
        self.ensure_one()
        user = self.env["res.users"].browse(user_id).exists()
        if user:
            self._process_user_signature(user)
        return True

    def _queued_mark_signature_mass_edit_done(self, processed_count):
        self.ensure_one()
        self._mark_signature_mass_edit_done(processed_count)
        return True
