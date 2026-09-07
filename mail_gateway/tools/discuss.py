# Copyright 2025 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.mail.tools.discuss import Store

original_one_id = Store.one_id


def extended_one_id(record, /, *, as_thread=False):
    result = original_one_id(record, as_thread=as_thread)
    # This patch is applied at import time, so it is shared by every registry
    # served by the process, while ``gateway_channel_ids`` only exists in the
    # registries where this module is installed. Check the actual registry.
    if (
        result
        and record._name == "res.partner"
        and "gateway_channel_ids" in record._fields
    ):
        result["gateway_channels"] = record.sudo().gateway_channel_ids.mail_format()
    return result


Store.one_id = staticmethod(extended_one_id)
