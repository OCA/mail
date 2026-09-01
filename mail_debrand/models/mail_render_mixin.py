# Copyright 2019 O4SB - Graeme Gellatly
# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2020 Onestein - Andrea Stirpe
# Copyright 2021 Tecnativa - João Marques
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import re

from lxml import etree, html
from markupsafe import Markup

from odoo import api, models

BODY_PLACEHOLDER = "<body_msg></body_msg>"
# Match the brand as a standalone word only. The look-behind and the
# look-ahead keep domain names (``odoo.com``, ``www.odoo.sh``), e-mail
# addresses, paths and longer identifiers (``OdooBot``) untouched, so only
# the branding written as prose is replaced.
BRAND_MENTION_RE = re.compile(
    r"(?<![\w./@-])odoo(?![\w@/]|[.-]\w)", flags=re.IGNORECASE
)
# ``re.split`` on this keeps the HTML tags in the resulting list, so the
# replacement can be applied to the text nodes only, never to an attribute.
HTML_TAG_RE = re.compile(r"(<[^>]*>)")


class MailRenderMixin(models.AbstractModel):
    _inherit = "mail.render.mixin"

    @api.model
    def _get_debrand_replacement(self):
        """Text that replaces the standalone brand mentions.

        It defaults to the name of the current company, which reads naturally
        in the sentences shipped by Odoo ("Welcome to Odoo", "Enjoy Odoo!",
        "A password reset was requested for the Odoo account..."). It can be
        overridden with the ``mail_debrand.brand_replacement`` configuration
        parameter, and setting that parameter to ``False`` disables the
        replacement altogether.

        :return: the replacement string, or ``None`` when disabled.
        """
        param = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("mail_debrand.brand_replacement", default=None)
        )
        if param is None:
            return self.env.company.name or ""
        # ``value`` is a required field on ir.config_parameter, so the way to
        # disable the feature is the "False" string.
        if param.strip().lower() in ("false", "none"):
            return None
        return param

    def remove_odoo_mentions(self, value):
        """Replace the brand mentions left in the text once the links are gone.

        Removing the ``odoo.com`` anchors is not enough for the templates that
        talk about the brand in plain words, such as the ones from
        ``auth_signup``. Only text nodes are processed, so URLs, e-mail
        addresses and any other attribute keep their value.
        """
        replacement = self._get_debrand_replacement()
        if replacement is None or not BRAND_MENTION_RE.search(value):
            return value
        chunks = HTML_TAG_RE.split(value)
        # Even indexes are text nodes, odd ones are the HTML tags themselves.
        chunks[::2] = [
            BRAND_MENTION_RE.sub(replacement, chunk) for chunk in chunks[::2]
        ]
        return "".join(chunks)

    def _remove_odoo_anchor(self, elem):
        """Drop an ``odoo.com`` anchor and the promotional text around it."""
        parent = elem.getparent()
        # Remove "Powered by", "using" etc.
        previous = elem.getprevious()
        if previous is not None:
            previous.tail = etree.CDATA("&nbsp;")
            # The link is usually the last line of a longer promotional block
            # (auth_signup's invitation mail). Drop the preceding text runs
            # that talk about the brand too, stopping at the first one that
            # belongs to the actual message.
            sibling = previous.getprevious()
            while sibling is not None:
                tail = sibling.tail or ""
                if tail.strip():
                    if not BRAND_MENTION_RE.search(tail):
                        break
                    sibling.tail = None
                sibling = sibling.getprevious()
        elif parent.text:
            parent.text = etree.CDATA("&nbsp;")
        parent.remove(elem)

    def remove_href_odoo(self, value, to_keep=None):
        if len(value) < 20:
            return value
        # value can be bytes or markup; ensure we get a proper string and preserve type
        back_to_bytes = False
        back_to_markup = False
        if isinstance(value, bytes):
            back_to_bytes = True
            value = value.decode()
        if isinstance(value, Markup):
            back_to_markup = True
        has_dev_odoo_link = re.search(
            r"<a\s(.*)dev\.odoo\.com", value, flags=re.IGNORECASE
        )
        has_odoo_link = re.search(r"<a\s(.*)odoo\.com", value, flags=re.IGNORECASE)
        # We don't want to change what was explicitly added in the message body,
        # so we will only change what is before and after it.
        if to_keep:
            value = value.replace(to_keep, BODY_PLACEHOLDER)
        if has_odoo_link and not has_dev_odoo_link:
            tree = html.fromstring(value)
            odoo_anchors = tree.xpath('//a[contains(@href,"odoo.com")]')
            for elem in odoo_anchors:
                self._remove_odoo_anchor(elem)
            value = etree.tostring(
                tree, pretty_print=True, method="html", encoding="unicode"
            )
        value = self.remove_odoo_mentions(value)
        if to_keep:
            value = value.replace(BODY_PLACEHOLDER, to_keep)
        if back_to_bytes:
            value = value.encode()
        elif back_to_markup:
            value = Markup(value)
        return value

    @api.model
    def _render_template(
        self,
        template_src,
        model,
        res_ids,
        engine="inline_template",
        add_context=None,
        options=None,
    ):
        """replace anything that is with odoo in templates
        if is a <a that contains odoo will delete it completely
        original:
         Render the given string on records designed by model / res_ids using
        the given rendering engine.

        :param str template_src: template text to render (jinja) or  (qweb)
          this could be cleaned but hey, we are in a rush
        :param str model: model name of records on which we want to perform rendering
        :param list res_ids: list of ids of records (all belonging to same model)
        :param string engine: inline_template, qweb or qweb_view;
        :param post_process: perform rendered str / html post processing (see
          ``_render_template_postprocess``)

        :return dict: {res_id: string of rendered template based on record}"""
        orginal_rendered = super()._render_template(
            template_src,
            model,
            res_ids,
            engine=engine,
            add_context=add_context,
            options=options,
        )

        for key in res_ids:
            orginal_rendered[key] = self.remove_href_odoo(orginal_rendered[key])

        return orginal_rendered
