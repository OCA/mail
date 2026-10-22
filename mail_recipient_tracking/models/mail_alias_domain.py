# Copyright 2020 Tecnativa - Alexandre Díaz
# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class MailAliasDomain(models.Model):
    _inherit = "mail.alias.domain"
    # `mail.alias.get_aliases` is cached, so invalidate it when alias domains change
    _clear_cache_name = "default"
    _clear_cache_on_fields = ("name", "catchall_alias", "default_from")
