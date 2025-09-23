# © 2023 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)

re = safe_eval.wrap_module(
    __import__("re"),
    [
        "compile",
        "escape",
        "findall",
        "finditer",
        "fullmatch",
        "match",
        "search",
        "sub",
        "subn",
    ],
)


class FetchmailRouting(models.Model):
    _name = "fetchmail.routing"
    _description = "Routing Extension of Incoming Servers"

    def _get_default_code(self):
        variables = self.default_variables()
        desc = "\n".join(f"# - {v}: {desc}" for v, desc in variables.items())
        return f"# Possible variables:\n{desc}\n\n"

    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    model_id = fields.Many2one(
        "ir.model",
        required=True,
        ondelete="cascade",
        help="The domain from the snippet is used on this model to assign e-mails to.",
    )
    code = fields.Text(default=lambda self: self._get_default_code())
    server_ids = fields.Many2many(
        "fetchmail.server",
        string="Allowed Servers",
        help="Limit the routing to only specific incoming e-mail servers",
    )
    help_text = fields.Html(compute="_compute_help_text", readonly=True, store=False)

    _sql_constraints = [
        ("name_uniq", "UNIQUE(name)", "The name must be unique!"),
    ]

    def _compute_help_text(self):
        lines = []
        for var, desc in self.default_variables().items():
            var = (f"<code>{v.strip()}</code>" for v in var.split(","))
            lines.append(f"<li>{', '.join(sorted(var))}: {desc}</li>")

        desc = "\n".join(lines)
        self.write({"help_text": f"<ul>{desc}</ul>"})

    @api.model
    def _get_eval_context(self):
        def log(message, *args, level="info"):
            level = {
                "debug": logging.DEBUG,
                "info": logging.INFO,
                "warning": logging.WARNING,
                "error": logging.ERROR,
                "critical": logging.CRITICAL,
            }.get(level, logging.INFO)
            _logger.log(level, message, *args)

        return {
            "datetime": safe_eval.datetime,
            "env": self.env,
            "log": log,
            "re": re,
            "time": safe_eval.time,
            "UserError": UserError,
        }

    def evaluate(self, ctx):
        self.ensure_one()
        safe_eval.safe_eval(self.code, ctx, mode="exec", nocopy=True)
        return ctx.get("result")

    @api.model
    def find_thread(self, message_dict, model=None, thread_id=None):
        return self.sudo()._find_thread(message_dict, model=model, thread_id=thread_id)

    @api.model
    def _find_thread(self, message_dict, model=None, thread_id=None):
        if model and thread_id:
            return model, thread_id

        email_from = message_dict.get("email_from")
        ctx = self._get_eval_context()
        ctx["email"] = {
            "from": (tools.email_split(email_from) or [""])[0].lower(),
            "subject": message_dict.get("subject") or "",
            "to": tools.email_split(message_dict.get("to")) or [],
            "recipients": tools.email_split(message_dict.get("recipients")) or [],
        }

        domain = []
        if model:
            domain.append(("model_id.model", "=", model))

        server = self.env.context.get("default_fetchmail_server_id")
        if server:
            domain += ["|", ("server_ids", "=", server), ("server_ids", "=", False)]

        for routing in self.search(domain).sorted("sequence"):
            domain = routing.evaluate(ctx)
            if not isinstance(domain, list | tuple):
                continue

            records = (
                self.env[routing.model_id.model]
                .with_context(active_test=False)
                .search(domain)
            )
            if len(records) > 1:
                raise ValueError(_("Too many records are matching"))

            if len(records) == 1:
                return records._name, records.id

        return model, thread_id

    def default_variables(self):
        """Informations about the available variables in the python code"""
        return {
            "email": "Dictionary with the parsed data from the email",
            "result": "Domain to find the correct record. Has to be set in the snippet",
            "log": "Logging functions",
            "env": "Odoo Environment on which the import is triggered",
            "datetime, re, time": "useful Python libraries",
            "UserError": "Warning Exception to use with raise",
        }
