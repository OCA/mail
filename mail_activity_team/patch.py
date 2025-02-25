from odoo import api, fields

from odoo.addons.mail.models.mail_activity import MailActivity


@api.model_create_multi
def mail_activity__create(self, vals_list):
    # Monkeypatch for mail's mail.activity's create method to prevent
    # UnboundLocalError: cannot access local variable 'activity' where it is not associated with a value
    # which occurs when this module creates activities without a user_id.
    # Patch below is according to https://github.com/odoo/odoo/pull/197864
    activities = super(MailActivity, self).create(vals_list)

    # find partners related to responsible users, separate readable from unreadable
    if any(user != self.env.user for user in activities.user_id):
        user_partners = activities.user_id.partner_id
        readable_user_partners = user_partners._filtered_access('read')
    else:
        readable_user_partners = self.env.user.partner_id

    # when creating activities for other: send a notification to assigned user;
    if self.env.context.get('mail_activity_quick_update'):
        activities_to_notify = self.env['mail.activity']
    else:
        activities_to_notify = activities.filtered(lambda act: act.user_id != self.env.user)
    if activities_to_notify:
        to_sudo = activities_to_notify.filtered(lambda act: act.user_id.partner_id not in readable_user_partners)
        other = activities_to_notify - to_sudo
        to_sudo.sudo().action_notify()
        other.action_notify()

    # subscribe (batch by model and user to speedup)
    for model, activity_data in activities._classify_by_model().items():
        per_user = dict()
        for activity in activity_data['activities'].filtered(lambda act: act.user_id):
            if activity.user_id not in per_user:
                per_user[activity.user_id] = [activity.res_id]
            else:
                per_user[activity.user_id].append(activity.res_id)
        for user, res_ids in per_user.items():
            pids = user.partner_id.ids if user.partner_id in readable_user_partners else user.sudo().partner_id.ids
            self.env[model].browse(res_ids).message_subscribe(partner_ids=pids)

    # send notifications about activity creation
    todo_activities = activities.filtered(lambda act: act.date_deadline <= fields.Date.today())
    if todo_activities:
        # Monkeypatch start
        # activity.user_id._bus_send("mail.activity/updated", {"activity_created": True})
        todo_activities.user_id._bus_send("mail.activity/updated", {"activity_created": True})
        # Monkeypatch end
    return activities
