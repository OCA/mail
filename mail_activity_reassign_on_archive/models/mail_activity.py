# Copyright 2026 Reinaldo J. Menendez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class MailActivity(models.Model):
    _inherit = "mail.activity"

    original_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Original Assignee",
        index=True,
        ondelete="set null",
        help="The user originally assigned to this activity before "
        "reassignment due to user archiving.",
    )

    def reassign_to_user(self, new_user):
        """Reassign activities to a new user, storing the original assignee.

        Groups activities by current user_id to minimize write operations.
        """
        for original_user, activities in self.grouped("user_id").items():
            _logger.info(
                f"Reassigning activities {activities} from user "
                f"{original_user.name} to user {new_user.name}"
            )
            activities.write(
                {
                    "original_user_id": original_user.id,
                    "user_id": new_user.id,
                }
            )

    def restore_to_original_user(self):
        """Restore activities back to their original assignees.

        Groups activities by original_user_id to minimize write operations.
        Only restores activities whose original user is still active.
        """
        to_restore = self.filtered(
            lambda a: a.original_user_id and a.original_user_id.active
        )
        for original_user, activities in to_restore.grouped("original_user_id").items():
            _logger.info(
                f"Restoring {activities} activities to original user "
                f"{original_user.name}"
            )
            activities.write(
                {
                    "user_id": original_user.id,
                    "original_user_id": False,
                }
            )
