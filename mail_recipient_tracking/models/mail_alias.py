# Copyright 2020 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class MailAlias(models.Model):
    _inherit = "mail.alias"
    # `get_aliases` is cached, so invalidate it when aliases change
    _clear_cache_name = "default"
    _clear_cache_on_fields = ("alias_name", "alias_domain_id")

    @api.model
    @api.ormcache()
    def get_aliases(self):
        """We want to discard these addresses for trackings"""
        aliases = {
            x["display_name"]
            for x in self.search_read([("alias_name", "!=", False)], ["display_name"])
        }
        mail_alias_domain = self.env["mail.alias.domain"].search_fetch(
            [], field_names=["catchall_email", "default_from", "default_from_email"]
        )
        catchall_emails = set(mail_alias_domain.mapped("catchall_email"))
        default_from_emails = set(
            mail_alias_domain.filtered("default_from").mapped("default_from_email")
        )
        return aliases | catchall_emails | default_from_emails
