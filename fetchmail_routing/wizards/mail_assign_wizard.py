# © 2024 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MailAssignWizard(models.TransientModel):
    _name = "mail.assign.wizard"
    _description = "E-Mail Assign Wizard"

    def _get_thread_models(self):
        return self.env["mail.unassigned"]._get_thread_models()

    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    operation = fields.Selection(
        [("new", "New Thread"), ("existing", "Existing Thread")],
        required=True,
    )
    mail_ids = fields.Many2many("mail.unassigned")
    thread_id = fields.Reference("_get_thread_models")
    model = fields.Selection("_get_thread_models")

    thread_per_mail = fields.Boolean(
        default=lambda self: self.env.company.assign_to_same_thread
    )
    show_same_thread = fields.Boolean(compute="_compute_show_same_thread")

    @api.depends("mail_ids", "operation")
    def _compute_show_same_thread(self):
        for rec in self:
            rec.show_same_thread = rec.operation == "new" and len(rec.mail_ids) > 1

    @api.onchange("operation")
    def _onchange_operation(self):
        if self.operation != "new":
            self.model = None
        if self.operation != "existing":
            self.thread_id = None

    def action_assign(self):
        self.ensure_one()

        if not self.mail_ids or not (self.thread_id or self.model):
            return

        if self.thread_id and self.model:
            raise ValidationError(_("Please select either an object or a thread"))

        mails = self.mail_ids.sorted("create_date")

        model = self.model or None
        thread = self.thread_id

        to_unlink = mails.browse()
        record_ids = set()
        if not self.thread_per_mail and self.model:
            mail, mails = mails[:1], mails[1:]
            mail.model = model
            thread_id = mail._assign_mail()

            if not thread_id:
                return

            thread, model = self.env[model].browse(thread_id), None
            to_unlink |= mail
            record_ids.add(thread_id)

        mails.write(
            {
                "thread_id": f"{thread._name},{thread.id}" if thread else None,
                "model": model,
            }
        )

        for mail in mails:
            thread_id = mail._assign_mail()
            if thread_id:
                record_ids.add(thread_id)
                to_unlink |= mail

        if to_unlink:
            to_unlink.unlink()

        if self.env.company.unassigned_show_after and record_ids:
            record_ids = tuple(record_ids)
            return {
                "type": "ir.actions.act_window",
                "name": _("Threads"),
                "res_model": model or thread._name,
                "view_mode": "list,form" if len(record_ids) > 1 else "form",
                "res_id": record_ids[0] if record_ids else None,
                "domain": [("id", "in", record_ids)],
            }
