# Copyright 2026 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, models

from odoo.addons.queue_job.utils import must_run_without_delay


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def _message_post_with_source_job_context_keys(self):
        """Context keys of the caller restored when the job posts the message.
        Jobs only keep a few safe keys of the context, so the ones that change
        how the message is sent have to be carried explicitly.
        """
        return ["force_send", "mail_notify_force_send"]

    def message_post_with_source(
        self,
        source_ref,
        render_values=None,
        message_type="notification",
        subtype_xmlid=False,
        subtype_id=False,
        **kwargs,
    ):
        post_kwargs = dict(
            kwargs,
            render_values=render_values,
            message_type=message_type,
            subtype_xmlid=subtype_xmlid,
            subtype_id=subtype_id,
        )
        template = self._get_source_from_ref(source_ref)[0]
        if (
            not template
            or not template.post_in_queue_job
            or self.env.context.get("job_uuid")
            or must_run_without_delay(self.env)
        ):
            return super().message_post_with_source(source_ref, **post_kwargs)
        job_context = {
            key: self.env.context[key]
            for key in self._message_post_with_source_job_context_keys()
            if key in self.env.context
        }
        for record in self:
            record.with_delay(
                description=self.env._(
                    "Post %(template)s on %(record)s",
                    template=template.display_name,
                    record=record.display_name,
                ),
            )._message_post_with_source_job(template, post_kwargs, job_context)
        return self.env["mail.message"]

    def _message_post_with_source_job(self, template, post_kwargs, job_context):
        record = self.exists()
        template = template.exists()
        if not record or not template:
            return self.env._("Nothing to post: the record or the template is gone.")
        record.with_context(**job_context).message_post_with_source(
            template, **post_kwargs
        )
