# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    """Fill record_name on the existing messages that mail.message.create would
    have filled, for the ones created before the module was installed.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute(
        """
        SELECT message.model, message.res_id, array_agg(message.id)
          FROM mail_message message
         WHERE (message.record_name IS NULL OR message.record_name = '')
           AND message.model IS NOT NULL
           AND message.res_id != 0
           AND message.message_type = 'notification'
           AND (
               message.body != ''
               OR EXISTS (
                   SELECT 1
                     FROM message_attachment_rel rel
                    WHERE rel.message_id = message.id
               )
           )
         GROUP BY message.model, message.res_id
        """
    )
    message_ids_per_document = defaultdict(dict)
    for model_name, res_id, message_ids in cr.fetchall():
        message_ids_per_document[model_name][res_id] = tuple(message_ids)
    for model_name, message_ids_per_res_id in message_ids_per_document.items():
        if model_name not in env:
            continue
        names = env["mail.message"]._get_record_names(
            model_name, list(message_ids_per_res_id)
        )
        for res_id, name in names.items():
            cr.execute(
                "UPDATE mail_message SET record_name = %s WHERE id IN %s",
                (name, message_ids_per_res_id[res_id]),
            )
    env["mail.message"].invalidate_model(["record_name"])
