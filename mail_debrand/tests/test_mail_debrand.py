# Copyright 2017 Tecnativa - Pedro M. Baeza
# Copyright 2020 Onestein - Andrea Stirpe
# Copyright 2021-22 Sodexis
# Copyright 2021 Tecnativa - João Marques
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common


class TestMailDebrand(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mail = cls.env["mail.mail"].create(
            {
                "email_from": "customer@example.com",
                "subject": "Hello",
                "email_to": "contact@example.com",
                "reply_to": "contact@example.com",
            }
        )
        lang_nl = cls.env.ref("base.lang_nl")
        if not lang_nl.active:
            lang_nl.toggle_active()

    def test_debrand_binary_value(self):
        """
        Regression test: ensure binary input is gracefully handled
        """
        try:
            self.env["mail.template"].remove_href_odoo(
                b"Binary value with more than 20 characters"
            )
        except TypeError:
            self.fail("Debranding binary string raised TypeError")

    def _test_debrand_by_lang(self, template_ref, lang, term):
        body = self.env["ir.qweb"]._render(
            template_ref,
            {
                "message": self.mail,
                "company": self.env.company,
                "email_notification_force_footer": True,
            },
            lang=lang.code,
            minimal_qcontext=True,
        )
        self.assertIn(term, body)
        body_cleaned = self.env["mail.render.mixin"].remove_href_odoo(body)
        self.assertNotIn(term, body_cleaned)

    def test_default_debrand(self):
        self._test_debrand_by_lang(
            "mail.mail_notification_layout",
            self.env.ref("base.lang_en"),
            "Powered by",
        )

    def test_default_debrand_translated(self):
        self._test_debrand_by_lang(
            "mail.mail_notification_layout",
            self.env.ref("base.lang_nl"),
            "Aangeboden door",
        )

    def test_light_debrand(self):
        self._test_debrand_by_lang(
            "mail.mail_notification_light",
            self.env.ref("base.lang_en"),
            "Powered by",
        )

    def test_light_debrand_translated(self):
        self._test_debrand_by_lang(
            "mail.mail_notification_light",
            self.env.ref("base.lang_nl"),
            "Aangeboden door",
        )

    def test_remove_odoo_mentions(self):
        """Standalone brand mentions are replaced by the company name"""
        mixin = self.env["mail.render.mixin"]
        company = self.env.company.name
        self.assertEqual(
            mixin.remove_odoo_mentions("<p>Welcome to Odoo. Enjoy Odoo!</p>"),
            f"<p>Welcome to {company}. Enjoy {company}!</p>",
        )

    def test_remove_odoo_mentions_keeps_technical_values(self):
        """URLs, e-mail addresses and identifiers are never touched"""
        mixin = self.env["mail.render.mixin"]
        for value in (
            '<a href="https://www.odoo.com?utm_source=db">Link</a>',
            "<p>Contact odoobot@example.com or odoo-support@example.com</p>",
            "<p>OdooBot created this record</p>",
            '<img src="/web/static/img/odoo-logo.png"/>',
            # A database named "odoo" ends up in the sign-in links
            '<a href="http://localhost:8069/web/login?db=odoo">Log in</a>',
        ):
            self.assertEqual(mixin.remove_odoo_mentions(value), value)

    def test_dev_odoo_link_disables_debranding(self):
        """A dev.odoo.com link marks the mail as one to leave alone"""
        value = (
            '<p>Ticket on <a href="https://dev.odoo.com/1">dev</a>, '
            'released by <a href="https://www.odoo.com">Odoo</a></p>'
        )
        result = self.env["mail.render.mixin"].remove_href_odoo(value)
        self.assertIn('href="https://www.odoo.com"', result)
        self.assertIn('href="https://dev.odoo.com/1"', result)

    def test_remove_odoo_mentions_custom_replacement(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "mail_debrand.brand_replacement", "Acme"
        )
        self.assertEqual(
            self.env["mail.render.mixin"].remove_odoo_mentions("<p>Enjoy Odoo!</p>"),
            "<p>Enjoy Acme!</p>",
        )

    def test_remove_odoo_mentions_disabled(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "mail_debrand.brand_replacement", "False"
        )
        value = "<p>Enjoy Odoo!</p>"
        self.assertEqual(
            self.env["mail.render.mixin"].remove_odoo_mentions(value), value
        )

    def test_body_intact(self):
        """The message body should never be changed"""
        MailMessage = self.env["mail.mail"]
        original_body = (
            "<p>And if I send odoo.example.com<br><br>And odoo.com"
            '<br><br>And <a target="_blank" rel="noreferrer noopener" '
            'href="https://odoo.com">https://odoo.com</a><br><br>And '
            '<a target="_blank" rel="noreferrer noopener" '
            'href="https://odoo.example.com">https://odoo.example.com</a></p>'
        )
        email_values = {
            "email_from": "customer@example.com",
            "subject": "Hello",
            "email_to": "contact@example.com",
            "reply_to": "contact@example.com",
            "body": original_body,
            "body_html": (
                "\n<div>\n\n\n<div><p>And if I send odoo.example.com<br><br>"
                'And odoo.com<br><br>And <a target="_blank" '
                'rel="noreferrer noopener" href="https://odoo.com">'
                'https://odoo.com</a><br><br>And <a target="_blank" '
                'rel="noreferrer noopener" href="https://odoo.example.com">'
                "https://odoo.example.com</a></p></div>\n\n"
                '<div style="font-size: 13px;"><span data-o-mail-quote="1">-- '
                '<br data-o-mail-quote="1">\nAdministrator</span></div>\n'
                '<p style="color: #555555; margin-top:32px;">\n    Sent\n    '
                '<span>\n    by\n    <a style="text-decoration:none; '
                'color: #875A7B;" href="http://www.example.com">\n        '
                "<span>YourCompany</span>\n    </a>\n    \n    </span>\n    "
                'using\n    <a target="_blank" '
                'href="https://www.odoo.com?utm_source=db&amp;utm_medium=email"'
                ' style="text-decoration:none; color: #875A7B;">Odoo'
                "</a>.\n</p>\n</div>\n        "
            ),
        }
        # No exception expected
        message = MailMessage.create(email_values)
        self.assertTrue(original_body in message._prepare_outgoing_body())
