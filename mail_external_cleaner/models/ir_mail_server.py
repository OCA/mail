import base64
import itertools
import mimetypes
import re

from odoo import models

_DATA_URI_RE = re.compile(
    r'src=(["\'])data:(?P<mime>[^;]+);base64,(?P<b64>[A-Za-z0-9+/=\s]+)\1',
    re.IGNORECASE,
)


def extract_inline_images_from_html(html, existing_names=()):
    """
    Finds <img src="data:...base64,..."> and returns:
      new_html, inline_attachments, inline_names
    where:
      - inline_attachments: list of (filename, bytes, mime) to append to your attachments
      - inline_names: set of the filenames we generated (these will become CIDs)
    """
    counter = itertools.count(1)
    existing = {n for n in existing_names if n}
    inline_attachments = []
    inline_names = set()

    def repl(m):
        mime = m.group("mime").strip().lower()
        ext = mimetypes.guess_extension(mime) or ".bin"
        # unique filename we’ll also use as the CID
        while True:
            name = f"inline-{next(counter)}{ext}"
            if name not in existing:
                break
        b64 = re.sub(r"\s+", "", m.group("b64"))
        data = base64.b64decode(b64)
        inline_attachments.append((name, data, mime))
        inline_names.add(name)
        return f'src="cid:{name}"'  # noqa: E231

    new_html = _DATA_URI_RE.sub(repl, html)
    return new_html, inline_attachments, inline_names


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    def build_email(
        self,
        email_from,
        email_to,
        subject,
        body,
        email_cc=None,
        email_bcc=None,
        reply_to=False,
        attachments=None,
        message_id=None,
        references=None,
        object_id=False,
        subtype="plain",
        headers=None,
        body_alternative=None,
        subtype_alternative="plain",
    ):
        existing_names = [
            a[0] for a in (attachments or []) if isinstance(a, (list, tuple)) and a
        ]
        if subtype == "html" and body:
            body, inline_atts, inline_names = extract_inline_images_from_html(
                body, existing_names
            )
        else:
            inline_atts, inline_names = [], set()
        # Append our inline attachments to your normal attachments (no function change)
        attachments = (attachments or []) + inline_atts
        msg = super().build_email(
            email_from,
            email_to,
            subject,
            body,
            email_cc=email_cc,
            email_bcc=email_bcc,
            reply_to=reply_to,
            attachments=attachments,
            message_id=message_id,
            references=references,
            object_id=object_id,
            subtype=subtype,
            headers=headers,
            body_alternative=body_alternative,
            subtype_alternative=subtype_alternative,
        )
        for part in msg.iter_attachments():
            fname = part.get_filename()
            if fname and fname in inline_names:
                # Content-ID used by <img src="cid:...">
                if "Content-ID" in part:
                    del part["Content-ID"]
                part.add_header("Content-ID", f"<{fname}>")

                # Inline disposition so clients don’t show them as regular downloads
                if part.get("Content-Disposition"):
                    part.replace_header(
                        "Content-Disposition",
                        f'inline; filename="{fname}"',  # noqa: E702
                    )
                else:
                    part.add_header(
                        "Content-Disposition",
                        f'inline; filename="{fname}"',  # noqa: E702
                    )

                # Ensure base64 transfer encoding (usually already set by add_attachment)
                cte = (part.get("Content-Transfer-Encoding") or "").lower()
                if cte != "base64":
                    payload = part.get_payload(decode=True)
                    part.set_payload(base64.b64encode(payload).decode("ascii"))
                    if cte:
                        part.replace_header("Content-Transfer-Encoding", "base64")
                    else:
                        part.add_header("Content-Transfer-Encoding", "base64")
        return msg
