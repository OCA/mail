from odoo import fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    conditional_attachment_ids = fields.One2many(
        "mail.template.conditional.attachment",
        "mail_template_id",
    )

    def _generate_template_attachments(
        self, res_ids, render_fields, render_results=None
    ):
        render_results = super()._generate_template_attachments(
            res_ids, render_fields, render_results
        )

        if self.conditional_attachment_ids:
            for res_id in res_ids:
                attachment_ids = self.conditional_attachment_ids.get_attachment_ids(
                    res_id
                )
                render_results[res_id]["attachment_ids"] = attachment_ids.ids
        return render_results
