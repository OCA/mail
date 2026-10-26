# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import json
import logging
import re

from odoo import api, models, tools

_logger = logging.getLogger(__name__)


class MailMail(models.Model):
    _inherit = "mail.mail"

    @api.model
    def _estimate_email_size(self, headers, body, attachments_size):
        """Estimate the email size, incorporating a small added security margin.

        :param dict headers: email headers
        :param str body: email body
        :param list attachments_size: list of attachment size in bytes
        """
        return (
            len(json.dumps(headers or {}, ensure_ascii=False).encode(errors="ignore"))
            + len((body or "").encode(errors="ignore"))
            + sum(attachments_size) * 8 / 6
            + 10  # 8 / 6 factor because base 64 are 6 bits coded in 8 bits
            * 1024  # adding 10Ko as security
        )

    def _prepare_outgoing_list(
        self, mail_server=False, recipients_follower_status=None
    ):
        """Return a list of emails to send based on current mail.mail. Each
        is a dictionary for specific email values, depending on a partner, or
        generic to the whole recipients given by mail.email_to.

        :param mail_server: <ir.mail_server> mail server that will be used to send the mails,
          False if it is the default one
        :param set recipients_follower_status: see ``Followers._get_mail_recipients_follower_status()``
        :return list: list of dicts used in IrMailServer.build_email()
        """
        self.ensure_one()
        body = self._prepare_outgoing_body()

        # headers
        headers = {}
        if self.headers:
            try:
                headers = ast.literal_eval(self.headers)
            except (ValueError, TypeError) as e:
                _logger.warning(
                    "Evaluation error when evaluating mail headers (received %r): %s",
                    self.headers,
                    e,
                )
            # global except as we don't want to crash the queue just due to a malformed
            # headers value
            except Exception as e:
                _logger.warning(
                    "Unknown error when evaluating mail headers (received %r): %s",
                    self.headers,
                    e,
                )
        headers.setdefault(
            "Return-Path",
            self.record_alias_domain_id.bounce_email or self.env.company.bounce_email,
        )

        # prepare recipients: use email_to if defined then check recipient_ids
        # that receive a specific email, notably due to link shortening / redirect
        # that is recipients-dependent. Keep original email/partner as this is
        # used in post-processing to know failures, like missing recipients
        email_list = []
        if self.email_to:
            email_to_normalized = tools.mail.email_normalize_all(self.email_to)
            email_to = tools.mail.email_split_and_format_normalize(self.email_to)
            email_list.append(
                {
                    "email_cc": [],
                    "email_to": email_to,
                    # list of normalized emails to help extract_rfc2822
                    "email_to_normalized": email_to_normalized,
                    # keep raw initial value for incoming pre processing of outgoing emails
                    "email_to_raw": self.email_to or "",
                    "partner_id": False,
                }
            )
        # add all cc once, either to the first "To", either as a single entry (do not mix
        # with partner-specific sending)
        if self.email_cc:
            if email_list:
                email_list[0]["email_cc"] = tools.mail.email_split_and_format_normalize(
                    self.email_cc
                )
                email_list[0]["email_to_normalized"] += tools.mail.email_normalize_all(
                    self.email_cc
                )
            else:
                email_list.append(
                    {
                        "email_cc": tools.mail.email_split_and_format_normalize(
                            self.email_cc
                        ),
                        "email_to": [],
                        "email_to_normalized": tools.mail.email_normalize_all(
                            self.email_cc
                        ),
                        "email_to_raw": False,
                        "partner_id": False,
                    }
                )
        # specific behavior to customize the send email for notified partners
        for partner in self.recipient_ids:
            # check partner email content
            email_to_normalized = tools.mail.email_normalize_all(partner.email)
            email_to = [
                tools.formataddr((partner.name or "", email or "False"))
                for email in email_to_normalized or [partner.email]
            ]
            email_list.append(
                {
                    "email_cc": [],
                    "email_to": email_to,
                    # list of normalized emails to help extract_rfc2822
                    "email_to_normalized": email_to_normalized,
                    # keep raw initial value for incoming pre processing of outgoing emails
                    "email_to_raw": partner.email or "",
                    "partner_id": partner,
                }
            )

        attachments = self.attachment_ids
        # Prepare attachments:
        # Remove attachments if user send the link with the access_token.
        if body and attachments:
            link_ids = {
                int(link)
                for link in re.findall(r"/web/(?:content|image)/([0-9]+)", body)
            }
            if link_ids:
                attachments = attachments - self.env["ir.attachment"].browse(
                    list(link_ids)
                )

        # Convert URL-only attachments (e.g. cloud or plain external links) into email links
        url_attachments = attachments.sudo().filtered(
            lambda a: a.url
            and not a.file_size
            and a.url.startswith(("http://", "https://", "ftp://"))
        )
        if url_attachments:
            url_attachments.sudo().generate_access_token()
            attachments_links = self.env["ir.qweb"]._render(
                "mail.mail_attachment_links", {"attachments": url_attachments}
            )
            body = tools.mail.append_content_to_html(
                body, attachments_links, plaintext=False
            )
            attachments -= url_attachments

        # Turn remaining attachments into links if they are too heavy and
        # their ownership are business models (i.e. something != mail.message,
        # otherwise they will be deleted along with the mail message leading to a 404)
        if record_owned_attachments := attachments.sudo().filtered(
            lambda a: a.res_model and a.res_id and a.res_model != "mail.message"
        ):
            estimated_email_size_bytes = self._estimate_email_size(
                headers, body, [a.file_size for a in attachments.sudo()]
            )
            max_email_size_bytes = (
                (mail_server or self.env["ir.mail_server"]).sudo()._get_max_email_size()
                * 1024
                * 1024
            )
            if estimated_email_size_bytes > max_email_size_bytes:
                # Remove attachments and prepare downloadable links to be added in the body
                record_owned_attachments.sudo().generate_access_token()
                attachments_links = self.env["ir.qweb"]._render(
                    "mail.mail_attachment_links",
                    {"attachments": record_owned_attachments},
                )
                body = tools.mail.append_content_to_html(
                    body, attachments_links, plaintext=False
                )
                attachments -= record_owned_attachments
        # Prepare the remaining attachment (those not embedded as link)
        # load attachment binary data with a separate read(), as prefetching all
        # `datas` (binary field) could bloat the browse cache, triggering
        # soft/hard mem limits with temporary data.
        email_attachments = [
            (a["name"], a["raw"], a["mimetype"])
            for a in attachments.sudo().read(["name", "raw", "mimetype"])
            if a["raw"] is not False
        ]

        # Build final list of email values with personalized body for recipient
        results = []
        for email_values in email_list:
            partner_id = email_values["partner_id"]
            body_personalized = self._personalize_outgoing_body(
                body, partner_id, recipients_follower_status
            )
            results.append(
                {
                    "attachments": email_attachments,
                    "body": body_personalized,
                    "body_alternative": tools.html2plaintext(body_personalized),
                    "email_cc": email_values["email_cc"],
                    "email_from": self.email_from,
                    "email_to": email_values["email_to"],
                    "email_to_normalized": email_values["email_to_normalized"],
                    "email_to_raw": email_values["email_to_raw"],
                    "headers": headers,
                    "message_id": self.message_id,
                    "object_id": f"{self.res_id}-{self.model}" if self.res_id else "",
                    "partner_id": partner_id,
                    "references": self.references,
                    "reply_to": self.reply_to,
                    "subject": self.subject,
                }
            )

        return results
