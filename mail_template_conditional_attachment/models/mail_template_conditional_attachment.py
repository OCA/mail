from odoo import api, models, fields
from odoo.tools import safe_eval
import datetime
import time
import dateutil


class MailTemplateConditionalAttachment(models.Model):
    _name = 'mail.template.conditional.attachment'
    _description = 'Mail Template Conditional Attachment'

    name = fields.Char('Description', required=True)

    mail_template_id = fields.Many2one(
        'mail.template',
        ondelete='cascade',
        required=True,
        index=True,
    )

    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Attachments',
    )

    model_name = fields.Char(related='mail_template_id.model_id.model')

    filter_domain = fields.Char(
        'Apply on',
        help='If present, this condition must be satisfied '
             'to include the attachments.',
    )

    def _get_eval_context(self):
        return {
            'datetime': datetime,
            'dateutil': dateutil,
            'time': time,
            'uid': self.env.uid,
            'user': self.env.user,
        }

    def _check_condition(self, res_id):
        self.ensure_one()
        if self.filter_domain:
            domain = [('id', '=', res_id)]
            domain += safe_eval(self.filter_domain, self._get_eval_context())
            model = self.env[self.model_name]
            return bool(model.search_count(domain))
        else:
            return True

    @api.multi
    def get_attachment_ids(self, res_id):
        self.mapped('mail_template_id').ensure_one()
        return self.filtered(
            lambda r: r._check_condition(res_id)).mapped('attachment_ids')
