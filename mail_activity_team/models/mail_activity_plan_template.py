from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MailActivityPlanTemplate(models.Model):
    _inherit = "mail.activity.plan.template"

    activity_team_id = fields.Many2one(
        comodel_name="mail.activity.team",
        compute="_compute_activity_team_id",
        ondelete="restrict",
        readonly=False,
        store=True,
    )
    activity_team_required = fields.Boolean(
        compute="_compute_activity_team_required",
        help="Indicate if this plan template must have an activity team",
    )
    # Add compute method to existing field
    responsible_id = fields.Many2one(
        compute="_compute_responsible_id",
        readonly=False,
        store=True,
    )
    responsible_type = fields.Selection(
        ondelete={"team": "set default"},
        selection_add=[("team", "Team")],
    )

    @api.depends("responsible_type")
    def _compute_activity_team_required(self):
        """Hook to override requiredness of activity team"""
        for template in self:
            template.activity_team_required = template.responsible_type == "team"

    @api.depends("activity_type_id", "responsible_type")
    def _compute_activity_team_id(self):
        """Assign the default team from the activity type"""
        for template in self:
            if template.activity_team_required:
                if template.activity_type_id.default_team_id:
                    template.activity_team_id = (
                        template.activity_type_id.default_team_id
                    )
            elif template.activity_team_id:
                template.activity_team_id = False

    @api.depends("responsible_type")
    def _compute_responsible_id(self):
        """Wipe responsible if field is not visible (c.q. allowed)"""
        for template in self:
            if template.activity_team_required and template.responsible_id:
                template.responsible_id = False

    @api.constrains("responsible_type", "activity_team_id")
    def _check_activity_team(self):
        for template in self:
            if template.activity_team_required and not template.activity_team_id:
                raise ValidationError(self.env._("Please enter an activity team."))

    def _determine_responsible(self, on_demand_responsible, applied_on_record):
        # Avoid signalling an error for a 'team' template without a user.
        self.ensure_one()
        if self.activity_team_required:
            return {"error": False}
        return super()._determine_responsible(on_demand_responsible, applied_on_record)
