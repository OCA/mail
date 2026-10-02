from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    absence_notified_user_ids = fields.Many2many(
        "res.users",
        string="Users Notified Today",
        readonly=True,
        copy=False,
        help="Users who have already been notified today about this absence",
    )
    absence_notified_date = fields.Date(
        string="Date of Last Absence Notification",
        readonly=True,
        copy=False,
        help="Date of the last notification record",
    )
