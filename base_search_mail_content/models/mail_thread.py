# Copyright 2016-17 ForgeFlow S.L.
#   (http://www.forgeflow.com)
# Copyright 2016 Serpent Consulting Services Pvt. Ltd.
#   (<http://www.serpentcs.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from lxml import etree

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools.sql import SQL

_MESSAGE_CONTENT_ILIKE_FIELDS = ("body",)
_MESSAGE_CONTENT_TRIGRAM_FIELDS = ("subject", "email_from", "reply_to")


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _search_message_content(self, operator, value):
        """Search mail thread records whose messages match ``value``.

        Build a domain on ``message_ids`` that searches across mail message
        body, subject, email_from and reply_to fields.

        The ``body`` field always uses ilike because HTML markup causes
        false positives with fuzzy matching.  The other fields use the
        PostgreSQL ``<%`` word-similarity operator when pg_trgm is
        available, otherwise fall back to standard LIKE/ILIKE.

        Negative operators (e.g. ``not ilike``) are handled by wrapping
        the sub-domain with ``not any`` on the ``message_ids`` field.
        """
        is_negative = operator in Domain.NEGATIVE_OPERATORS
        op = Domain.NEGATIVE_OPERATORS.get(operator, operator)
        content_domain = self._get_message_content_domain(op, value)
        model_domain = Domain("model", "=", self._name) & content_domain
        any_op = "not any" if is_negative else "any"
        return Domain("message_ids", any_op, model_domain)

    def _get_message_content_domain(self, operator, value):
        """Return a domain on ``mail.message`` matching ``value``.

        The ``body`` field always uses ilike because HTML markup causes
        false positives with fuzzy matching.  The other fields use pg_trgm
        fuzzy search (``<%`` operator) when available, falling back to
        standard LIKE/ILIKE otherwise.
        """
        all_fields = _MESSAGE_CONTENT_ILIKE_FIELDS + _MESSAGE_CONTENT_TRIGRAM_FIELDS
        if (
            operator.endswith("like")
            and self.env.registry.has_trigram
            and isinstance(value, str)
        ):
            msg_ids = self._trigram_message_ids(value)
            if msg_ids is not None:
                body_domain = Domain.OR(
                    Domain(f, operator, value) for f in _MESSAGE_CONTENT_ILIKE_FIELDS
                )
                return Domain("id", "in", list(msg_ids)) | body_domain
        return Domain.OR(Domain(field, operator, value) for field in all_fields)

    def _trigram_message_ids(self, value):
        """Return ids of mail.messages whose content matches ``value`` using pg_trgm.

        Execute a raw SQL query using the PostgreSQL ``<%`` word-similarity
        operator (provided by pg_trgm) to find messages with fuzzy-matching
        content.  Only searches ``_MESSAGE_CONTENT_TRIGRAM_FIELDS``; the
        ``body`` field is excluded because HTML markup causes false positives.

        The similarity threshold is set to 0.3 for the current transaction,
        matching upstream's ``Website._trigram_enumerate_words`` behaviour.

        For translated fields, also search in all JSONB translation values
        using ``jsonb_path_query_array``.

        Returns ``None`` if the query fails (e.g. pg_trgm not installed).
        """
        Message = self.env["mail.message"].sudo()
        unaccent = self.env.registry.unaccent
        search = unaccent(SQL("%s", value))
        conditions = []
        for field_name in _MESSAGE_CONTENT_TRIGRAM_FIELDS:
            field = Message._fields[field_name]
            field_sql = Message._field_to_sql(Message._table, field_name, SQL())
            if field.translate:
                jsonb_sql = unaccent(
                    SQL(
                        "jsonb_path_query_array(%s, '$.*')::text",
                        Message._field_to_sql(Message._table, field_name, SQL()),
                    )
                )
                conditions.append(
                    SQL(
                        "(%(search)s <%% %(jsonb)s OR %(search)s <%% %(field)s)",
                        search=search,
                        jsonb=jsonb_sql,
                        field=unaccent(field_sql),
                    )
                )
            else:
                conditions.append(
                    SQL(
                        "%(search)s <%% %(field)s",
                        search=search,
                        field=unaccent(field_sql),
                    )
                )
        try:
            Message.env.cr.execute("SET LOCAL pg_trgm.word_similarity_threshold TO 0.3")
            Message.env.cr.execute(
                SQL(
                    "SELECT id FROM mail_message WHERE model = %s AND (%s)",
                    SQL("%s", self._name),
                    SQL(" OR ").join(conditions),
                ),
            )
            return {row[0] for row in Message.env.cr.fetchall()}
        except Exception:
            return None

    message_content = fields.Text(
        help="Message content, to be used only in searches",
        compute="_compute_message_content",
        search="_search_message_content",
    )

    def _compute_message_content(self):
        """Always assign False to avoid CacheMiss on non-stored field."""
        self.message_content = False

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        """Inject ``message_content`` field into every search view.

        Append an ``<field name="message_content" operator="ilike"/>``
        element after the last search field so users can fuzzy-search
        across mail message content from any mail.thread model.
        """
        res = super().get_view(view_id=view_id, view_type=view_type, options=options)
        if (
            view_type == "search"
            and self._fields.get("message_content")
            and self.env.user.has_group("base.group_user")
        ):
            doc = etree.XML(res["arch"])
            for node in doc.xpath("/search/field[last()]"):
                elem = etree.Element(
                    "field", {"name": "message_content", "operator": "ilike"}
                )
                node.addnext(elem)
                res["arch"] = etree.tostring(doc, encoding="unicode")
        return res
