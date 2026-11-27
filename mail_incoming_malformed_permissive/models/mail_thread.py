# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import copy
import logging
import re

from lxml import (
    etree,
)
from lxml import (
    html as lxml_html,
)

from odoo import models
from odoo.tools import html_sanitize

_logger = logging.getLogger(__name__)

HTML_OPENING_TAG = re.compile(r"<\s*html\b[^>]*>", re.IGNORECASE)
HTML_CLOSING_TAG = re.compile(r"<\s*/\s*html\s*>", re.IGNORECASE)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _message_parse_extract_payload(
        self, message, message_dict, save_original=False
    ):
        if not self.env.company.parse_all_html_documents_in_mail:
            return super()._message_parse_extract_payload(
                message, message_dict, save_original=save_original
            )
        fixed_message = self._merge_html_documents(message)
        payload = super()._message_parse_extract_payload(
            fixed_message,
            message_dict,
            # use save_original=False, otherwise it will always save the copy
            save_original=False,
        )
        if save_original:
            # Save the mail as received, not the fixed copy
            payload["attachments"].insert(
                0, self._Attachment("original_email.eml", message.as_string(), {})
            )
        return payload

    def _merge_html_documents(self, message):
        """Keep every ``<html>`` of each html part, not just the first one.

        Return a fixed copy, to keep ``message`` as received.
        """
        fixed_message = copy.deepcopy(message)
        for part in fixed_message.walk():
            if part.get_content_type() != "text/html" or part.is_attachment():
                continue
            content = self._parse_whole_html_part(part.get_content())
            if content is not None:
                part.set_content(content, subtype="html")
        return fixed_message

    def _parse_whole_html_part(self, html_content):
        """Keep every ``<html>`` of the part, not just the first one.

        Return ``None`` if there is a single ``<html>`` or parsing fails.
        """
        if len(HTML_OPENING_TAG.findall(html_content)) < 2:
            return None

        # Turn each <html> into a <div>, wrapped in a single <html>
        html_content = HTML_OPENING_TAG.sub("<div>", html_content)
        html_content = HTML_CLOSING_TAG.sub("</div>", html_content)
        html_content = f"<html>{html_content}</html>"
        try:
            root = lxml_html.fromstring(html_content)
            return html_sanitize(
                lxml_html.tostring(root, encoding="unicode"),
                sanitize_tags=False,
                strip_classes=True,
            )
        except (etree.ParserError, ValueError):
            _logger.warning("Could not parse the HTML part of an incoming mail")
        return None
