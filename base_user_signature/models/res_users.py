# Copyright 2004-2010 OpenERP SA (<http://www.openerp.com>)
# Copyright 2011-2015 Serpent Consulting Services Pvt. Ltd.
# Copyright 2017 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    digital_signature = fields.Image(
        copy=False,
        max_width=1024,
        max_height=1024,
        user_writeable=True,
    )

    def clear_digital_signature(self):
        self.digital_signature = False
