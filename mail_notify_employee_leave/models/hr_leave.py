from odoo import models


class HrLeave(models.Model):
    _inherit = "hr.leave"

    def _validate_leave_request(self):
        """
        Override _validate_leave_request to skip absence notifications when
        approving leaves. The context flag 'skip_absence_notification' prevents
        _notify_thread from sending messages,
        """
        return super(
            HrLeave, self.with_context(skip_absence_notification=True)
        )._validate_leave_request()
