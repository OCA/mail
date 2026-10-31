from odoo.tests import TransactionCase, tagged

from odoo.addons.mail_debrand.models.mail_render_mixin import (
    BRAND_MENTION_RE,
    HTML_TAG_RE,
)


@tagged("-at_install", "post_install")
class TestMailDebrandSignup(TransactionCase):
    def _has_module(self):
        module = self.env["ir.module.module"].search([("name", "=", "auth_signup")])
        self.assertTrue(module)
        return module.state == "installed"

    def _assert_debranded(self, body):
        """No standalone brand mention is left in the visible text.

        Only the text nodes are checked, exactly like the debranding itself:
        the URLs are none of its business, and a database literally named
        "odoo" would otherwise make this fail on its own sign-in link.
        """
        for text in HTML_TAG_RE.split(body)[::2]:
            self.assertFalse(
                BRAND_MENTION_RE.search(text),
                f"Brand mention left in the rendered mail: {text}",
            )

    def test_debrand_auth_signup_set_password_email(self):
        if not self._has_module():
            return
        template = self.env.ref(
            "auth_signup.set_password_email",
        )
        self.assertIn("www.odoo.com", template.body_html)
        self.assertIn("Accept invitation", template.body_html)
        self.assertIn("to discover the tool", template.body_html)
        self.assertIn("Never heard of Odoo?", template.body_html)

        mail_id = template.send_mail(self.env.user.id)
        mail = self.env["mail.mail"].browse(mail_id)
        body = mail.body_html

        # The essential button is preserved
        self.assertIn("Accept invitation", body)
        # The branding is gone, links and prose alike
        self.assertNotIn("www.odoo.com", body)
        self.assertNotIn("to discover the tool", body)
        # The promotional block that came with the removed link goes with it
        self.assertNotIn("Never heard of", body)
        self._assert_debranded(body)
        # ... and so does the branding of the subject
        self._assert_debranded(mail.subject)
        # The company name took its place, so the sentences still read well
        self.assertIn(f"Welcome to {self.env.company.name}", body)

    def test_debrand_auth_signup_reset_password_email(self):
        """The reset password mail is rendered from a qweb view, not a template."""
        if not self._has_module():
            return
        view = self.env.ref("auth_signup.reset_password_email")
        user = self.env.user
        # Same call as auth_signup's ``_action_reset_password``
        body = self.env["mail.render.mixin"]._render_template(
            view,
            model="res.users",
            res_ids=user.ids,
            engine="qweb_view",
            options={"post_process": True},
        )[user.id]
        mail = (
            self.env["mail.mail"]
            .sudo()
            .create(
                {
                    "subject": "Password reset",
                    "email_from": "noreply@example.com",
                    "email_to": "user@example.com",
                    "body_html": body,
                }
            )
        )
        outgoing_body = mail._prepare_outgoing_body()
        # The action link is preserved
        self.assertIn("Change password", outgoing_body)
        self._assert_debranded(outgoing_body)

    def test_record_data_is_not_debranded(self):
        """Only the branding is replaced, never the data of the records."""
        if not self._has_module():
            return
        user = self.env["res.users"].create(
            {
                "name": "OdooBot Sanchez",
                "login": "odoobot.sanchez@example.com",
                "email": "odoobot.sanchez@example.com",
            }
        )
        template = self.env.ref("auth_signup.set_password_email")
        mail_id = template.send_mail(user.id)
        body = self.env["mail.mail"].browse(mail_id).body_html
        self.assertIn("OdooBot Sanchez", body)
        self.assertIn("odoobot.sanchez@example.com", body)
        self._assert_debranded(body)
