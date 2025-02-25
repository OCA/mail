from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Update noupdate ir.rule data record"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    rule = env.ref("mail_activity_team.mail_activity_rule_my_team")
    rule.domain_force = "[('team_id', 'in', user.activity_team_ids.ids)]"
    rule.perm_create = False
