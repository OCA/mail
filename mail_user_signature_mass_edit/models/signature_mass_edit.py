# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class SignatureMassEdit(models.Model):
    _name = "signature.mass.edit"
    _description = "Signature Mass Edit"
    _order = "id desc"

    signature = fields.Html(string="Signature Template", required=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    group_ids = fields.Many2many(
        comodel_name="res.groups",
        string="Groups",
        help="Apply the signature only to users belonging to at least one of "
        "these groups. Leave empty to apply it to all company users.",
    )
    state = fields.Selection(
        selection=[("draft", "Draft"), ("done", "Done")],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        default="draft",
    )
    user_count = fields.Integer(string="Users", compute="_compute_user_count")
    processed_user_count = fields.Integer(
        string="Processed Users", readonly=True, copy=False
    )

    @api.depends("company_id", "group_ids")
    def _compute_display_name(self):
        for record in self:
            if not record.company_id:
                record.display_name = self.env._("Signature Mass Edit")
                continue
            display_name = self.env._(
                "Signature Mass Edit - %(company)s", company=record.company_id.name
            )
            if record.group_ids:
                group_names = ", ".join(record.group_ids.mapped("display_name"))
                display_name = self.env._(
                    "%(display_name)s (%(groups)s)",
                    display_name=display_name,
                    groups=group_names,
                )
            record.display_name = display_name

    @api.depends("company_id", "group_ids")
    def _compute_user_count(self):
        for record in self:
            record.user_count = len(record._get_target_users())

    def action_confirm(self):
        for record in self:
            record._check_can_confirm()
            record._process_signature_mass_edit()
        return True

    def action_view_users(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Users"),
            "res_model": "res.users",
            "view_mode": "list,form",
            "views": [
                (False, "list"),
                (self.env.ref("base.view_users_form").id, "form"),
            ],
            "domain": self._get_target_users_domain(),
        }

    def action_reset_to_draft(self):
        self.write({"state": "draft"})
        return True

    def _check_can_confirm(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(
                self.env._("Only draft signature mass edits can be confirmed.")
            )

    def _get_target_users_domain(self):
        self.ensure_one()
        internal_user_group = self.env.ref("base.group_user")
        domain = [
            ("active", "=", True),
            ("company_ids", "in", self.company_id.id),
            ("groups_id", "in", internal_user_group.id),
        ]
        if self.group_ids:
            domain.append(("groups_id", "in", self.group_ids.ids))
        return domain

    def _get_target_users(self):
        self.ensure_one()
        return self.env["res.users"].sudo().search(self._get_target_users_domain())

    def _process_signature_mass_edit(self):
        self.ensure_one()
        users = self._get_target_users()
        for user in users:
            self._process_user_signature(user)
        self._mark_signature_mass_edit_done(len(users))

    def _process_user_signature(self, user):
        self.ensure_one()
        user.ensure_one()
        rendered_signatures = (
            self.env["mail.render.mixin"]
            .sudo()
            ._render_template(
                self.signature,
                "res.users",
                user.ids,
                engine="inline_template",
                options={"post_process": True},
            )
        )
        user.sudo().write({"signature": rendered_signatures.get(user.id, "")})

    def _mark_signature_mass_edit_done(self, processed_count):
        self.ensure_one()
        self.write({"processed_user_count": processed_count, "state": "done"})
