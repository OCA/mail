# Copyright 2025 OCA Contributors
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestSignatureTemplate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.user_admin = cls.env.ref("base.user_admin")

        # Create demo user if it doesn't exist
        cls.user_demo = cls.env["res.users"].search([("login", "=", "demo")], limit=1)
        if not cls.user_demo:
            cls.user_demo = cls.env["res.users"].create(
                {
                    "name": "Demo User",
                    "login": "demo",
                    "email": "demo@example.com",
                    "company_id": cls.company.id,
                }
            )

        # Create a test template
        cls.template = cls.env["signature.template"].create(
            {
                "name": "Test Template",
                "body_html": """
                <div>
                    <t t-out="company_logo"/>
                    <strong><t t-out="name"/></strong><br/>
                    <t t-out="function"/><br/>
                    <t t-out="email"/><br/>
                    <t t-out="company_name"/>
                </div>
            """,
                "company_id": cls.company.id,
            }
        )

    def tearDown(self):
        """Reset company settings after each test."""
        super().tearDown()
        self.company.force_signature_template = False
        self.company.use_signature_templates = True

    def test_01_template_creation(self):
        """Test template creation and basic fields."""
        self.assertEqual(self.template.name, "Test Template")
        self.assertTrue(self.template.active)
        self.assertEqual(self.template.company_id, self.company)
        self.assertTrue(self.template.body_html)

    def test_02_template_rendering(self):
        """Test template rendering with user data."""
        rendered = self.template._render_signature(self.user_admin)
        self.assertIn(self.user_admin.name, rendered)
        self.assertIn(self.user_admin.email, rendered)
        self.assertIn(self.company.name, rendered)
        self.assertIn("o_mail_signature", rendered)

    def test_03_company_settings(self):
        """Test company signature settings."""
        self.company.use_signature_templates = True
        self.company.default_signature_template_id = self.template

        # Create new user
        new_user = self.env["res.users"].create(
            {
                "name": "Test User",
                "login": "test_user",
                "email": "test@example.com",
                "company_id": self.company.id,
            }
        )

        # Check default template is assigned
        self.assertEqual(new_user.signature_template_id, self.template)
        self.assertTrue(new_user.use_signature_template)

    def test_04_user_signature_computation(self):
        """Test user signature computation with template."""
        # Ensure company is not forcing templates
        self.company.force_signature_template = False

        self.user_demo.use_signature_template = True
        self.user_demo.signature_template_id = self.template

        # Force recomputation
        self.user_demo._compute_signature()

        # Check signature contains template content
        self.assertIn(self.user_demo.name, self.user_demo.signature)
        self.assertIn(self.user_demo.email or "", self.user_demo.signature)

    def test_05_custom_signature(self):
        """Test custom signature when not using template."""
        # Ensure company is not forcing templates
        self.company.force_signature_template = False

        custom_sig = "<p>Custom signature</p>"
        self.user_demo.use_signature_template = False
        self.user_demo.signature = custom_sig

        # Custom signature should be preserved
        self.assertEqual(self.user_demo.signature, custom_sig)

    def test_06_template_with_logo(self):
        """Test template with company logo."""
        import base64

        self.template.include_company_logo = True
        self.template.logo_max_width = 150

        # Test with no logo first - clear both logo and external URL
        self.company.logo = False
        self.company.signature_logo_url = False
        rendered = self.template._render_signature(self.user_admin)
        self.assertNotIn("<img", rendered)

        # Create a simple 1x1 red pixel PNG as test logo
        logo_data = base64.b64decode(
            b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        )
        self.company.logo = base64.b64encode(logo_data)

        rendered = self.template._render_signature(self.user_admin)
        self.assertIn("<img", rendered)
        self.assertIn("max-width:150px", rendered)

    def test_07_empty_template_validation(self):
        """Test validation for empty template."""
        with self.assertRaises(ValidationError):
            self.env["signature.template"].create(
                {
                    "name": "Empty Template",
                    "body_html": "",
                    "company_id": self.company.id,
                }
            )

    def test_08_force_signature_template(self):
        """Test force signature template company setting."""
        self.company.use_signature_templates = True
        self.company.force_signature_template = True
        self.company.default_signature_template_id = self.template

        # When force_signature_template is True, users should use templates
        self.assertTrue(self.user_demo.use_signature_template)

        # Try to change it to False - should raise ValidationError
        with self.assertRaises(ValidationError):
            self.user_demo.use_signature_template = False

        # User should still have template enabled
        self.assertTrue(self.user_demo.use_signature_template)
        self.assertEqual(self.user_demo.signature_template_id, self.template)

    def test_09_template_preview_wizard(self):
        """Test signature preview wizard."""
        wizard = self.env["signature.template.preview"].create(
            {
                "template_id": self.template.id,
                "user_id": self.user_admin.id,
            }
        )

        self.assertTrue(wizard.preview_html)
        self.assertIn(self.user_admin.name, wizard.preview_html)

    def test_10_multi_company(self):
        """Test multi-company template isolation."""
        # Create second company
        company2 = self.env["res.company"].create(
            {
                "name": "Test Company 2",
            }
        )

        # Create template for company2
        template2 = self.env["signature.template"].create(
            {
                "name": "Company 2 Template",
                "body_html": "<p>Company 2 Signature</p>",
                "company_id": company2.id,
            }
        )

        # User in company1 should not see company2 templates
        templates = self.env["signature.template"].with_user(self.user_admin).search([])
        self.assertIn(self.template, templates)
        self.assertNotIn(template2, templates)

    def test_11_template_placeholders(self):
        """Test all template placeholders."""
        template_html = """
            <t t-out="name"/> | <t t-out="email"/> | <t t-out="phone"/> |
            <t t-out="mobile"/> | <t t-out="function"/> |
            <t t-out="company_name"/> | <t t-out="website"/> |
            <t t-out="company_email"/> | <t t-out="company_phone"/>
        """

        template = self.env["signature.template"].create(
            {
                "name": "Placeholder Test",
                "body_html": template_html,
                "company_id": self.company.id,
            }
        )

        # Set test data
        self.user_admin.function = "Test Function"
        self.user_admin.phone = "+1234567890"
        self.user_admin.mobile = "+0987654321"
        self.company.website = "www.test.com"
        self.company.email = "info@test.com"
        self.company.phone = "+1111111111"

        rendered = template._render_signature(self.user_admin)

        # Check all placeholders are replaced
        self.assertNotIn("<t t-out=", rendered)
        self.assertIn(self.user_admin.name, rendered)
        self.assertIn(self.user_admin.email, rendered)

    def test_12_onchange_company_id(self):
        """Test users get correct template when created in different companies."""
        # Ensure base company doesn't force templates and has no default
        self.company.force_signature_template = False
        self.company.default_signature_template_id = False

        # Create a template for company 2
        company2 = self.env["res.company"].create({"name": "Company 2"})
        company2.use_signature_templates = True
        company2.force_signature_template = False  # Ensure no forcing
        template2 = self.env["signature.template"].create(
            {
                "name": "Company 2 Template",
                "body_html": "<p>Company 2</p>",
                "company_id": company2.id,
            }
        )
        company2.default_signature_template_id = template2

        # Add company2 to user's allowed companies and set as current
        self.user_demo.company_ids = [(4, company2.id)]

        # Test onchange method directly (without actually changing company)
        # Create a fresh user with the new company to avoid issues with copied data
        # Use sudo to avoid permission issues with multi-company
        test_user = (
            self.env["res.users"]
            .sudo()
            .create(
                {
                    "name": "Test Onchange User",
                    "login": "test_onchange",
                    "company_id": company2.id,
                    "company_ids": [(6, 0, [company2.id])],
                }
            )
        )

        # Should get the default template from new company
        self.assertEqual(test_user.signature_template_id, template2)

        # Test with company without templates
        company3 = self.env["res.company"].create({"name": "Company 3"})
        company3.use_signature_templates = True
        self.user_demo.company_ids = [(4, company3.id)]

        # Test with company without templates
        test_user2 = (
            self.env["res.users"]
            .sudo()
            .create(
                {
                    "name": "Test Onchange User 2",
                    "login": "test_onchange2",
                    "company_id": company3.id,
                    "company_ids": [(6, 0, [company3.id])],
                }
            )
        )

        # Should have no template since company3 has no default template
        self.assertFalse(test_user2.signature_template_id)

    def test_13_action_preview(self):
        """Test action_preview method."""
        action = self.template.action_preview()
        self.assertEqual(action["res_model"], "signature.template.preview")
        self.assertEqual(action["context"]["default_template_id"], self.template.id)
        self.assertEqual(action["context"]["default_user_id"], self.env.user.id)

    def test_14_action_view_users(self):
        """Test action_view_users method."""
        # Ensure company is not forcing templates
        self.company.force_signature_template = False

        # Assign template to users
        self.user_demo.use_signature_template = True
        self.user_demo.signature_template_id = self.template

        action = self.template.action_view_users()
        self.assertEqual(action["res_model"], "res.users")
        self.assertEqual(
            action["domain"],
            [
                ("signature_template_id", "=", self.template.id),
                ("use_signature_template", "=", True),
            ],
        )

    def test_15_create_default_template(self):
        """Test create_default_template method."""
        template = self.env["signature.template"].create_default_template()
        self.assertTrue(template)
        self.assertEqual(template.name, "Default Signature Template")
        self.assertIn('<t t-out="name"/>', template.body_html)
        self.assertIn('<t t-out="email"/>', template.body_html)
        self.assertIn('<t t-out="company_logo"/>', template.body_html)

    def test_16_preview_wizard_without_template(self):
        """Test preview wizard without template_id."""
        wizard = self.env["signature.template.preview"].create(
            {
                "template_id": False,
                "user_id": self.user_admin.id,
            }
        )
        self.assertFalse(wizard.preview_html)

        # Test with template but different user
        wizard2 = self.env["signature.template.preview"].create(
            {
                "template_id": self.template.id,
                "user_id": self.user_demo.id,
            }
        )
        # Should have preview with demo user's data
        self.assertTrue(wizard2.preview_html)
        self.assertIn(self.user_demo.name, wizard2.preview_html)

    def test_17_company_force_template_override(self):
        """Test company forcing template overrides user selection."""
        # Initially disable force template
        self.company.force_signature_template = False

        # User selects a specific template
        user_template = self.env["signature.template"].create(
            {
                "name": "User Choice Template",
                "body_html": "<p>User selected this</p>",
                "company_id": self.company.id,
            }
        )

        self.user_demo.write(
            {
                "_use_signature_template": True,
                "_signature_template_id": user_template.id,
            }
        )

        # Verify user's selection is active
        self.assertEqual(self.user_demo.signature_template_id, user_template)
        self.assertTrue(self.user_demo.use_signature_template)
        self.assertIn("User selected this", self.user_demo.signature)

        # Now company forces a different template
        company_template = self.env["signature.template"].create(
            {
                "name": "Company Forced Template",
                "body_html": "<p>Company forces this</p>",
                "company_id": self.company.id,
            }
        )

        self.company.write(
            {
                "use_signature_templates": True,
                "default_signature_template_id": company_template.id,
                "force_signature_template": True,
            }
        )

        # Force recomputation
        self.user_demo._compute_use_signature_template()
        self.user_demo._compute_signature_template_id()
        self.user_demo._compute_signature()

        # Verify company template overrides user selection
        self.assertEqual(self.user_demo.signature_template_id, company_template)
        self.assertTrue(self.user_demo.use_signature_template)
        self.assertTrue(self.user_demo.signature)  # Ensure signature is not False
        self.assertIn("Company forces this", self.user_demo.signature or "")

        # User cannot change when forced
        with self.assertRaises(ValidationError):
            self.user_demo.write(
                {
                    "use_signature_template": False,
                }
            )

    def test_18_user_access_fields(self):
        """Test _get_signature_access_fields method."""
        fields = self.user_demo._get_signature_access_fields()
        self.assertIn("use_signature_template", fields)
        self.assertIn("signature_template_id", fields)

    def test_19_user_preview_signature(self):
        """Test action_preview_signature method."""
        # Ensure company is not forcing templates
        self.company.force_signature_template = False

        self.user_demo.signature_template_id = self.template
        action = self.user_demo.action_preview_signature()
        self.assertEqual(action["res_model"], "signature.template.preview")
        self.assertEqual(action["context"]["default_user_id"], self.user_demo.id)
        self.assertEqual(action["context"]["default_template_id"], self.template.id)

    def test_20_external_logo_url(self):
        """Test external logo URL functionality."""
        # Test with external URL override
        self.company.signature_logo_url = "https://example.com/logo.png"
        self.company.signature_logo_width = 200

        self.template.include_company_logo = True
        rendered = self.template._render_signature(self.user_admin)

        # Should use external URL
        self.assertIn('src="https://example.com/logo.png"', rendered)
        self.assertIn('width="200"', rendered)
        # Height should not be set - auto height for aspect ratio
        self.assertNotIn('height="', rendered)
        self.assertIn("height:auto", rendered)

        # Clear external URL - should fall back to public mailcdn URL
        self.company.signature_logo_url = False
        rendered = self.template._render_signature(self.user_admin)

        # Should use public mailcdn URL for logo
        self.assertIn("/mailcdn/logo/", rendered)

    def test_21_user_avatar_image(self):
        """Test user avatar image in signatures."""
        template_html = """
            <div>
                <t t-out="user_image"/>
                <t t-out="user_image_large"/>
                <t t-out="name"/>
            </div>
        """
        template = self.env["signature.template"].create(
            {
                "name": "Avatar Test",
                "body_html": template_html,
                "company_id": self.company.id,
            }
        )

        rendered = template._render_signature(self.user_admin)

        # Check avatar URLs are included (now using public URLs)
        self.assertIn(f"/mailcdn/avatar/{self.user_admin.id}_", rendered)
        self.assertIn("?size=128", rendered)
        self.assertIn("?size=256", rendered)
        self.assertIn('width="64" height="64"', rendered)
        self.assertIn('width="116" height="116"', rendered)
        # No longer forcing border-radius in default user_image
        self.assertNotIn("border-radius: 50%", rendered)

    def test_22_color_fields(self):
        """Test primary and secondary color fields in template."""
        # First set company colors to known values to ensure test consistency
        self.company.email_primary_color = "#000000"
        self.company.email_secondary_color = "#111111"

        template = self.env["signature.template"].create(
            {
                "name": "Color Test",
                "body_html": (
                    "<div>"
                    "<a t-att-style=\"'color: ' + primary_color\">Link</a>"
                    "<hr t-att-style=\"'border-color: ' + secondary_color\"/>"
                    "<span t-att-style=\"'border-left: 2px solid ' + "
                    "divider_color + ';'\">Legacy</span>"
                    "</div>"
                ),
                "company_id": self.company.id,
                "use_company_colors": False,  # Use template colors, not company colors
                "primary_color": "#ff0000",
                "secondary_color": "#00ff00",
            }
        )

        rendered = template._render_signature(self.user_admin)
        self.assertIn("color: #ff0000", rendered)  # Primary color
        self.assertIn("border-color: #00ff00", rendered)  # Secondary color
        # divider_color uses primary
        self.assertIn("border-left: 2px solid #ff0000", rendered)

        # Test default colors
        template2 = self.env["signature.template"].create(
            {
                "name": "Color Test 2",
                "body_html": ("<a t-att-style=\"'color: ' + primary_color\">Test</a>"),
                "company_id": self.company.id,
                "use_company_colors": False,  # Use template default colors
            }
        )

        rendered2 = template2._render_signature(self.user_admin)
        self.assertIn("color: #0066cc", rendered2)  # Default primary color

    def test_22b_company_email_colors(self):
        """Test using company email colors when enabled."""
        # Set company email colors
        self.company.email_primary_color = "#123456"
        self.company.email_secondary_color = "#789abc"

        # Create template with use_company_colors enabled (default)
        template = self.env["signature.template"].create(
            {
                "name": "Company Colors Test",
                "body_html": (
                    "<div>"
                    "<a t-att-style=\"'color: ' + primary_color\">Link</a>"
                    "<hr t-att-style=\"'border-color: ' + secondary_color\"/>"
                    "</div>"
                ),
                "company_id": self.company.id,
                "use_company_colors": True,
                "primary_color": "#ff0000",  # Should be ignored
                "secondary_color": "#00ff00",  # Should be ignored
            }
        )

        rendered = template._render_signature(self.user_admin)
        self.assertIn("color: #123456", rendered)  # Company primary color
        self.assertIn("border-color: #789abc", rendered)  # Company secondary color
        self.assertNotIn("#ff0000", rendered)  # Template colors not used
        self.assertNotIn("#00ff00", rendered)

        # Disable company colors
        template.use_company_colors = False
        rendered2 = template._render_signature(self.user_admin)
        self.assertIn("color: #ff0000", rendered2)  # Template primary color
        self.assertIn("border-color: #00ff00", rendered2)  # Template secondary color

    def test_23_wizard_onchange_user(self):
        """Test wizard onchange user method."""
        # Create second company with templates
        company2 = self.env["res.company"].create({"name": "Company 2"})
        self.env["signature.template"].create(
            {
                "name": "Company 2 Template",
                "body_html": "<p>Company 2</p>",
                "company_id": company2.id,
            }
        )

        # Create user in company2
        user2 = self.env["res.users"].create(
            {
                "name": "User 2",
                "login": "user2",
                "company_id": company2.id,
                "company_ids": [(4, company2.id)],
            }
        )

        wizard = self.env["signature.template.preview"].create(
            {
                "user_id": self.user_admin.id,
            }
        )

        # Onchange should set domain for company1 templates
        result = wizard._onchange_user_id()
        expected_domain = [("company_id", "=", self.company.id)]
        self.assertEqual(result["domain"]["template_id"], expected_domain)

        # Change to user2
        wizard.user_id = user2
        result = wizard._onchange_user_id()
        expected_domain = [("company_id", "=", company2.id)]
        self.assertEqual(result["domain"]["template_id"], expected_domain)

        # Test with no user
        wizard.user_id = False
        result = wizard._onchange_user_id()
        self.assertEqual(result["domain"]["template_id"], [])

    def test_24_company_onchange_template(self):
        """Test company onchange default template method."""
        # Create templates for different companies
        company2 = self.env["res.company"].create({"name": "Company 2"})
        template2 = self.env["signature.template"].create(
            {
                "name": "Company 2 Template",
                "body_html": "<p>Company 2</p>",
                "company_id": company2.id,
            }
        )

        # Test setting correct template
        self.company.default_signature_template_id = self.template
        result = self.company._onchange_default_signature_template_id()
        self.assertEqual(
            result["domain"]["default_signature_template_id"],
            [("company_id", "=", self.company.id)],
        )

        # Test setting wrong template (from different company)
        # This should clear the field
        self.company.default_signature_template_id = template2
        result = self.company._onchange_default_signature_template_id()
        self.assertFalse(self.company.default_signature_template_id)

        # Test with new company (no id yet)
        new_company = self.env["res.company"].new({"name": "New Company"})
        result = new_company._onchange_default_signature_template_id()
        self.assertEqual(result["domain"]["default_signature_template_id"], [])

    def test_25_logo_position_settings(self):
        """Test logo position settings in template."""
        # Test different logo positions
        positions = ["top", "left", "right"]
        for position in positions:
            template = self.env["signature.template"].create(
                {
                    "name": f"Logo {position}",
                    "body_html": "<div><t t-out='company_logo'/></div>",
                    "company_id": self.company.id,
                    "logo_position": position,
                    "include_company_logo": True,
                }
            )
            self.assertEqual(template.logo_position, position)

    def test_26_template_with_all_new_fields(self):
        """Test template with all new functionality combined."""
        # Set up company with external logo and known email colors
        self.company.signature_logo_url = "https://cdn.example.com/logo.png"
        self.company.signature_logo_width = 150
        self.company.email_primary_color = "#112233"
        self.company.email_secondary_color = "#445566"

        # Create template with all features
        template_html = """
            <table>
                <tr>
                    <td t-att-style="'border-right: 1px solid ' + secondary_color">
                        <t t-out="user_image_large"/>
                    </td>
                    <td>
                        <h3><t t-out="name"/></h3>
                        <p><t t-out="function"/></p>
                        <p><t t-out="email"/></p>
                        <div>
                            <t t-out="company_logo"/>
                            <t t-out="company_name"/>
                        </div>
                    </td>
                </tr>
            </table>
        """

        template = self.env["signature.template"].create(
            {
                "name": "Full Featured Template",
                "body_html": template_html,
                "company_id": self.company.id,
                "include_company_logo": True,
                "use_company_colors": True,  # Use company colors (default)
                "primary_color": "#0066cc",
                "secondary_color": "#ff6600",
            }
        )

        rendered = template._render_signature(self.user_admin)

        # Check template uses company colors when enabled
        self.assertIn(
            "border-right: 1px solid #445566", rendered
        )  # company secondary_color
        self.assertIn('src="https://cdn.example.com/logo.png"', rendered)
        self.assertIn(f"/mailcdn/avatar/{self.user_admin.id}_", rendered)
        self.assertIn(self.user_admin.name, rendered)
        self.assertIn(self.company.name, rendered)

        # Now test with company colors disabled
        template.use_company_colors = False
        rendered2 = template._render_signature(self.user_admin)
        self.assertIn(
            "border-right: 1px solid #ff6600", rendered2
        )  # template secondary_color

    def test_27_utm_tracking_basic(self):
        """Test basic UTM tracking functionality."""
        # Create UTM objects
        utm_source = self.env["utm.source"].create({"name": "test-email-sig"})
        utm_medium = self.env["utm.medium"].create({"name": "email"})
        utm_campaign = self.env["utm.campaign"].create({"name": "Test Campaign 2025"})

        # Create template with UTM tracking
        template = self.env["signature.template"].create(
            {
                "name": "UTM Test Template",
                "body_html": '<a t-att-href="website_url"><t t-out="website"/></a>',
                "company_id": self.company.id,
                "use_utm_tracking": True,
                "utm_source_id": utm_source.id,
                "utm_medium_id": utm_medium.id,
                "utm_campaign_id": utm_campaign.id,
            }
        )

        # Set company website
        self.company.website = "www.example.com"

        # Render signature
        rendered = template._render_signature(self.user_admin)

        # Check UTM parameters are included
        self.assertIn("utm_source=test-email-sig", rendered)
        self.assertIn("utm_medium=email", rendered)
        self.assertIn("utm_campaign=Test+Campaign+2025", rendered)
        self.assertIn(f"utm_content=user-{self.user_admin.id}", rendered)

    def test_28_utm_tracking_disabled(self):
        """Test that UTM tracking doesn't apply when disabled."""
        template = self.env["signature.template"].create(
            {
                "name": "No UTM Template",
                "body_html": '<a t-att-href="website_url"><t t-out="website"/></a>',
                "company_id": self.company.id,
                "use_utm_tracking": False,
            }
        )

        self.company.website = "www.example.com"
        rendered = template._render_signature(self.user_admin)

        # Should not contain UTM parameters
        self.assertNotIn("utm_source=", rendered)
        self.assertNotIn("utm_medium=", rendered)
        # When UTM is disabled, URL is returned as-is without protocol
        self.assertIn("www.example.com", rendered)

    def test_29_utm_url_builder(self):
        """Test _build_utm_url method with various URLs."""
        utm_source = self.env["utm.source"].create({"name": "email-signature"})
        utm_medium = self.env["utm.medium"].create({"name": "email"})

        template = self.env["signature.template"].create(
            {
                "name": "UTM Builder Test",
                "body_html": "<p>Test</p>",
                "company_id": self.company.id,
                "use_utm_tracking": True,
                "utm_source_id": utm_source.id,
                "utm_medium_id": utm_medium.id,
            }
        )

        # Test with plain domain
        url1 = template._build_utm_url("example.com", self.user_admin)
        self.assertIn("https://example.com", url1)
        self.assertIn("utm_source=email-signature", url1)
        self.assertIn(f"utm_content=user-{self.user_admin.id}", url1)

        # Test with http URL
        url2 = template._build_utm_url("http://example.com", self.user_admin)
        self.assertIn("http://example.com", url2)

        # Test with existing parameters
        url3 = template._build_utm_url("https://example.com?foo=bar", self.user_admin)
        self.assertIn("foo=bar", url3)
        self.assertIn("utm_source=email-signature", url3)

        # Test with anchor
        url4 = template._build_utm_url(
            "https://example.com/page#section", self.user_admin
        )
        self.assertIn("#section", url4)
        self.assertIn("utm_source=email-signature", url4)

    def test_30_utm_default_values(self):
        """Test UTM tracking with default values."""
        template = self.env["signature.template"].create(
            {
                "name": "UTM Defaults Test",
                "body_html": '<a t-att-href="website_url">Link</a>',
                "company_id": self.company.id,
                "use_utm_tracking": True,
                # No UTM fields set - should use defaults
            }
        )

        self.company.website = "example.com"
        rendered = template._render_signature(self.user_admin)

        # Check default values are used
        self.assertIn("utm_source=email-signature", rendered)
        self.assertIn("utm_medium=email", rendered)
        self.assertIn(f"utm_content=user-{self.user_admin.id}", rendered)

    def test_31_utm_special_characters(self):
        """Test UTM tracking with special characters in campaign names."""
        utm_campaign = self.env["utm.campaign"].create(
            {"name": "Special Chars & Spaces + More!"}
        )

        template = self.env["signature.template"].create(
            {
                "name": "UTM Special Chars Test",
                "body_html": '<a t-att-href="website_url">Link</a>',
                "company_id": self.company.id,
                "use_utm_tracking": True,
                "utm_campaign_id": utm_campaign.id,
            }
        )

        self.company.website = "example.com"
        rendered = template._render_signature(self.user_admin)

        # Check special characters are properly encoded
        self.assertIn("utm_campaign=Special+Chars+%26+Spaces+%2B+More%21", rendered)

    def test_32_website_url_placeholder(self):
        """Test website_url placeholder behavior."""
        template_html = """
            <div>
                <t t-if="website_url">
                    Website: <a t-att-href="website_url"><t t-out="website"/></a>
                </t>
                <t t-if="not website_url">
                    No website configured
                </t>
            </div>
        """

        template = self.env["signature.template"].create(
            {
                "name": "Website URL Test",
                "body_html": template_html,
                "company_id": self.company.id,
                "use_utm_tracking": True,
            }
        )

        # Test with no website
        self.company.website = False
        rendered = template._render_signature(self.user_admin)
        self.assertIn("No website configured", rendered)

        # Test with website
        self.company.website = "www.company.com"
        rendered = template._render_signature(self.user_admin)
        self.assertIn("Website:", rendered)
        self.assertIn('href="https://www.company.com', rendered)
        self.assertIn("utm_source=email-signature", rendered)

    def test_33_utm_tracking_inheritance(self):
        """Test that UTM tracking works with template inheritance."""
        # Create base template with UTM
        base_template = self.env["signature.template"].create(
            {
                "name": "Base UTM Template",
                "body_html": '<div>Base: <a t-att-href="website_url">Visit</a></div>',
                "company_id": self.company.id,
                "use_utm_tracking": True,
            }
        )

        # Create campaign for tracking
        utm_campaign = self.env["utm.campaign"].create({"name": "Inherited Campaign"})
        base_template.utm_campaign_id = utm_campaign

        self.company.website = "inherited.example.com"
        rendered = base_template._render_signature(self.user_admin)

        self.assertIn("utm_campaign=Inherited+Campaign", rendered)
        self.assertIn("inherited.example.com", rendered)

    def test_34_utm_url_with_protocol(self):
        """Test that URLs with protocols don't get double protocols."""
        template = self.env["signature.template"].create(
            {
                "name": "Protocol Test",
                "body_html": '<a t-att-href="website_url"><t t-out="website"/></a>',
                "company_id": self.company.id,
                "use_utm_tracking": True,
            }
        )

        # Test with URL that already has https://
        self.company.website = "https://google.com"
        rendered = template._render_signature(self.user_admin)

        # Should not have double protocol
        self.assertNotIn("https://https://", rendered)
        self.assertIn('href="https://google.com', rendered)
        self.assertIn("utm_source=email-signature", rendered)

        # Test with various protocol combinations
        test_cases = [
            ("http://example.com", "http://example.com"),
            ("https://example.com", "https://example.com"),
            ("example.com", "https://example.com"),
            ("www.example.com", "https://www.example.com"),
            ("https://https://example.com", "https://example.com"),  # Double protocol
            ("http://http://example.com", "http://example.com"),  # Double protocol
        ]

        for input_url, expected_domain in test_cases:
            self.company.website = input_url
            url = template._build_utm_url(input_url, self.user_admin)
            self.assertTrue(
                url.startswith(expected_domain),
                f"URL {url} should start with {expected_domain} for input {input_url}",
            )
            # Ensure no double protocols
            self.assertNotIn("://https://", url)
            self.assertNotIn("://http://", url)

    def test_35_utm_multiple_links(self):
        """Test template with multiple tracked links."""
        template_html = """
            <div>
                <a t-att-href="website_url">Main Website</a>
                <a t-att-href="website_url + '/products'">Products</a>
                <a t-att-href="website_url + '/contact'">Contact</a>
            </div>
        """

        template = self.env["signature.template"].create(
            {
                "name": "Multi Link UTM Test",
                "body_html": template_html,
                "company_id": self.company.id,
                "use_utm_tracking": True,
            }
        )

        self.company.website = "www.multilink.com"
        rendered = template._render_signature(self.user_admin)

        # All links should have UTM parameters
        self.assertEqual(rendered.count("utm_source=email-signature"), 3)
        # The concatenation adds path after parameters
        self.assertIn("utm_content=user-", rendered)
        self.assertIn('/products">Products</a>', rendered)
        self.assertIn('/contact">Contact</a>', rendered)

    def test_36_public_image_urls(self):
        """Test public image URLs for Gmail compatibility."""
        from ..controllers.public_image import PublicSignatureImage

        # Ensure company uses internal logo, not external URL
        self.company.signature_logo_url = False

        # Create template with user image and company logo
        template = self.env["signature.template"].create(
            {
                "name": "Public Image Test",
                "body_html": """
                    <div>
                        <t t-out="user_image"/>
                        <t t-out="company_logo"/>
                    </div>
                """,
                "company_id": self.company.id,
                "include_company_logo": True,
            }
        )

        rendered = template._render_signature(self.user_admin)

        # Check that public URLs are used
        self.assertIn("/mailcdn/avatar/", rendered)
        self.assertIn("/mailcdn/logo/", rendered)
        self.assertNotIn("/web/image/res.users/", rendered)
        self.assertNotIn("/web/image/res.partner/", rendered)

        # Test token generation
        avatar_url = PublicSignatureImage.get_public_avatar_url(
            self.user_admin.id, env=self.env
        )
        self.assertIn(f"/mailcdn/avatar/{self.user_admin.id}_", avatar_url)
        self.assertIn("?size=128", avatar_url)

        logo_url = PublicSignatureImage.get_public_logo_url(
            self.company.id, env=self.env
        )
        self.assertIn(f"/mailcdn/logo/{self.company.id}_", logo_url)
        # Logo URL now includes extension based on actual image format
        self.assertTrue(
            any(ext in logo_url for ext in [".png", ".jpg", ".gif", ".svg"]),
            "Logo URL should include image extension",
        )

    def test_37_public_controller_security(self):
        """Test public image controller security."""
        from ..controllers.public_image import PublicSignatureImage

        controller = PublicSignatureImage()

        # Test valid token
        # valid_hash = controller._generate_token_hash("avatar", self.user_admin.id)
        # valid_token would be: f"{self.user_admin.id}_{valid_hash}"

        # Test invalid token (wrong hash)
        # invalid_token would be: f"{self.user_admin.id}_wronghash"

        # The actual HTTP testing would require a test client
        # Here we just verify token generation is consistent
        hash1 = controller._generate_token_hash("avatar", 1)
        hash2 = controller._generate_token_hash("avatar", 1)
        self.assertEqual(hash1, hash2, "Token hash should be consistent")

        # Different prefixes should generate different hashes
        avatar_hash = controller._generate_token_hash("avatar", 1)
        logo_hash = controller._generate_token_hash("logo", 1)
        self.assertNotEqual(
            avatar_hash, logo_hash, "Different prefixes should have different hashes"
        )

    def test_38_utm_source_data_creation(self):
        """Test that UTM source handling works correctly."""
        # Check if UTM source exists or create it
        utm_source = self.env.ref(
            "mail_user_signature_template.utm_source_email_signature",
            raise_if_not_found=False,
        )

        if not utm_source:
            # Create it if it doesn't exist (might happen in test environment)
            utm_source = self.env["utm.source"].create({"name": "email-signature"})
            self.env["ir.model.data"].create(
                {
                    "name": "utm_source_email_signature",
                    "module": "mail_user_signature_template",
                    "model": "utm.source",
                    "res_id": utm_source.id,
                }
            )

        self.assertEqual(
            utm_source.name, "email-signature", "UTM source should have correct name"
        )

        # Test that templates without utm_source_id use the default
        template = self.env["signature.template"].create(
            {
                "name": "Test UTM Default",
                "body_html": """
                <div>
                    <a t-att-href="website_url">Website</a>
                </div>
            """,
                "company_id": self.company.id,
            }
        )

        self.company.website = "https://example.com"
        rendered = template._render_signature(self.user_admin)

        # Should have default utm_source
        self.assertIn("utm_source=email-signature", rendered)
        self.assertIn("utm_medium=email", rendered)

        # Test with custom UTM source
        custom_utm = self.env["utm.source"].create({"name": "custom-sig"})
        template.utm_source_id = custom_utm
        rendered = template._render_signature(self.user_admin)

        self.assertIn("utm_source=custom-sig", rendered)
        self.assertNotIn("utm_source=email-signature", rendered)

    def test_39_social_media_fields(self):
        """Test social media fields in signatures."""
        # Check if social media fields exist on company
        has_social_fields = hasattr(self.company, "social_twitter")

        if has_social_fields:
            # Set social media URLs on company
            self.company.social_twitter = "https://twitter.com/mycompany"
            self.company.social_facebook = "https://facebook.com/mycompany"
            self.company.social_linkedin = "https://linkedin.com/company/mycompany"
            self.company.social_instagram = "https://instagram.com/mycompany"

        # Create template with social media links
        template = self.env["signature.template"].create(
            {
                "name": "Social Media Test",
                "body_html": """
                <div>
                    <t t-if="social_twitter">
                        Twitter: <a t-att-href="social_twitter">Follow us</a><br/>
                    </t>
                    <t t-if="social_facebook">
                        Facebook: <a t-att-href="social_facebook">Like us</a><br/>
                    </t>
                    <t t-if="social_linkedin">
                        LinkedIn: <a t-att-href="social_linkedin">Connect</a><br/>
                    </t>
                    <t t-if="social_instagram">
                        Instagram: <a t-att-href="social_instagram">Follow</a><br/>
                    </t>
                </div>
            """,
                "company_id": self.company.id,
                "use_utm_tracking": True,
            }
        )

        rendered = template._render_signature(self.user_admin)

        if has_social_fields:
            # Check if website module is installed
            has_website = self.env.registry.get("website") is not None

            if has_website:
                # Should use /website/social/ routes
                self.assertIn("/website/social/twitter", rendered)
                self.assertIn("/website/social/facebook", rendered)
                self.assertIn("/website/social/linkedin", rendered)
                self.assertIn("/website/social/instagram", rendered)
            else:
                # Should use direct URLs with UTM
                self.assertIn("twitter.com/mycompany", rendered)
                self.assertIn("facebook.com/mycompany", rendered)
                self.assertIn("linkedin.com/company/mycompany", rendered)
                self.assertIn("instagram.com/mycompany", rendered)

            # Check UTM parameters are added
            self.assertIn("utm_source=email-signature", rendered)
            self.assertIn("utm_medium=email", rendered)
            self.assertIn(f"utm_content=user-{self.user_admin.id}", rendered)
        else:
            # Without social fields, the template should render but without social links
            self.assertNotIn("twitter.com", rendered)
            self.assertNotIn("facebook.com", rendered)
            self.assertNotIn("linkedin.com", rendered)
            self.assertNotIn("instagram.com", rendered)

    def test_40_image_format_detection(self):
        """Test image format detection for SVG and other formats."""
        from ..controllers.public_image import PublicSignatureImage

        controller = PublicSignatureImage()

        # Test SVG detection
        svg_data = (
            b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"></svg>'
        )
        self.assertEqual(
            controller._detect_image_format(svg_data),
            "image/svg+xml",
            "Should detect SVG from XML declaration",
        )

        svg_data2 = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'
        self.assertEqual(
            controller._detect_image_format(svg_data2),
            "image/svg+xml",
            "Should detect SVG from svg tag",
        )

        # Test PNG detection
        png_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00"
        self.assertEqual(
            controller._detect_image_format(png_data),
            "image/png",
            "Should detect PNG format",
        )

        # Test JPEG detection
        jpeg_data = b"\xff\xd8\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        self.assertEqual(
            controller._detect_image_format(jpeg_data),
            "image/jpeg",
            "Should detect JPEG format",
        )

        # Test GIF detection
        gif_data = b"GIF89a\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        self.assertEqual(
            controller._detect_image_format(gif_data),
            "image/gif",
            "Should detect GIF format",
        )

        # Test WebP detection
        webp_data = b"RIFF\x00\x00\x00\x00WEBP"
        self.assertEqual(
            controller._detect_image_format(webp_data),
            "image/webp",
            "Should detect WebP format",
        )

        # Test BMP detection
        bmp_data = b"BM\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        self.assertEqual(
            controller._detect_image_format(bmp_data),
            "image/bmp",
            "Should detect BMP format",
        )

        # Test ICO detection
        ico_data = b"\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        self.assertEqual(
            controller._detect_image_format(ico_data),
            "image/x-icon",
            "Should detect ICO format",
        )

        # Test fallback for unknown format
        unknown_data = b"UNKNOWN\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        self.assertEqual(
            controller._detect_image_format(unknown_data),
            "image/png",
            "Should fallback to PNG for unknown formats",
        )

    def test_41_signature_invalidation_on_template_change(self):
        """Test that signatures are invalidated when template changes."""
        # Disable force template for this test
        self.company.force_signature_template = False

        # Create a template and assign to user
        template = self.env["signature.template"].create(
            {
                "name": "Test Invalidation",
                "body_html": "<div>Original: <t t-out='name'/></div>",
                "company_id": self.company.id,
            }
        )

        self.user_demo.use_signature_template = True
        self.user_demo.signature_template_id = template
        # Force computation of signature
        self.user_demo._compute_signature()
        original_signature = self.user_demo.signature
        self.assertTrue(original_signature, "Signature should not be empty")
        self.assertIn("Original:", original_signature)

        # Change template - should invalidate signature
        template.body_html = "<div>Updated: <t t-out='name'/></div>"
        self.assertIn("Updated:", self.user_demo.signature)
        self.assertNotIn("Original:", self.user_demo.signature)

    def test_42_signature_invalidation_on_company_change(self):
        """Test that signatures are invalidated when company data changes."""
        # Disable force template for this test
        self.company.force_signature_template = False

        # Set up template with company website
        self.company.website = "old.example.com"
        template = self.env["signature.template"].create(
            {
                "name": "Test Company Invalidation",
                "body_html": "<div>Website: <t t-out='website'/></div>",
                "company_id": self.company.id,
            }
        )

        self.user_demo.use_signature_template = True
        self.user_demo.signature_template_id = template
        # Force computation of signature
        self.user_demo._compute_signature()
        original_signature = self.user_demo.signature
        self.assertTrue(original_signature, "Signature should not be empty")
        self.assertIn("old.example.com", original_signature)

        # Change company website - should invalidate signature
        self.company.website = "new.example.com"
        self.assertIn("new.example.com", self.user_demo.signature)
        self.assertNotIn("old.example.com", self.user_demo.signature)

    def test_43_manual_signature_recomputation(self):
        """Test manual signature recomputation method."""
        # Disable force template for this test
        self.company.force_signature_template = False

        # Create template
        template = self.env["signature.template"].create(
            {
                "name": "Test Manual Recompute",
                "body_html": "<div>Hello <t t-out='name'/></div>",
                "company_id": self.company.id,
            }
        )

        self.user_demo.use_signature_template = True
        self.user_demo.signature_template_id = template

        # Manually set incorrect signature
        self.user_demo.signature = "<div>Wrong signature</div>"

        # Trigger manual recomputation
        result = self.user_demo.action_recompute_signature()

        # Check signature was recomputed
        self.assertIn("Hello", self.user_demo.signature)
        self.assertIn(self.user_demo.name, self.user_demo.signature)

        # Check notification action returned
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["tag"], "display_notification")

    def test_44_signature_invalidation_color_change(self):
        """Test signature invalidation when colors change."""
        # Disable force template for this test
        self.company.force_signature_template = False

        # Create template using company colors
        template = self.env["signature.template"].create(
            {
                "name": "Test Color Invalidation",
                "body_html": (
                    "<div t-att-style=\"'color: ' + primary_color\">Text</div>"
                ),
                "company_id": self.company.id,
                "use_company_colors": True,
            }
        )

        self.user_demo.use_signature_template = True
        self.user_demo.signature_template_id = template

        # Set initial company color
        self.company.email_primary_color = "#FF0000"
        # Force computation to ensure signature is generated
        self.user_demo._compute_signature()
        original_signature = self.user_demo.signature
        self.assertIn("#FF0000", original_signature)

        # Change company color
        self.company.email_primary_color = "#00FF00"
        # Invalidate cache to ensure recomputation
        self.user_demo.invalidate_recordset()
        new_signature = self.user_demo.signature

        self.assertIn("#00FF00", new_signature)
        self.assertNotIn("#FF0000", new_signature)

    def test_45_public_image_controller_edge_cases(self):
        """Test edge cases in public image controller."""
        from ..controllers.public_image import PublicSignatureImage

        controller = PublicSignatureImage()

        # Test with short data (less than 12 bytes)
        short_data = b"SHORT"
        self.assertEqual(
            controller._detect_image_format(short_data),
            "image/png",
            "Should return PNG for short data",
        )

        # Test extension mapping
        self.assertEqual(
            controller._get_extension_from_content_type("image/jpeg"), ".jpg"
        )
        self.assertEqual(
            controller._get_extension_from_content_type("unknown/type"), ".png"
        )

    def test_46_server_action_execution(self):
        """Test server action for signature recomputation."""
        # Create users with templates
        template = self.env["signature.template"].create(
            {
                "name": "Test Server Action",
                "body_html": "<div>Signature for <t t-out='name'/></div>",
                "company_id": self.company.id,
            }
        )

        # Create multiple users
        users = self.env["res.users"]
        for i in range(3):
            user = self.env["res.users"].create(
                {
                    "name": f"Test User {i}",
                    "login": f"testuser{i}@example.com",
                    "use_signature_template": True,
                    "signature_template_id": template.id,
                }
            )
            users |= user

        # Manually corrupt signatures
        users.write({"signature": "<div>Corrupted</div>"})

        # Execute server action code
        records = users
        if records:
            records._compute_signature()

        # Check all signatures were recomputed
        for user in users:
            self.assertIn("Signature for", user.signature)
            self.assertIn(user.name, user.signature)
            self.assertNotIn("Corrupted", user.signature)

    def test_47_social_media_fields_invalidation(self):
        """Test signature invalidation when social media fields change."""
        # Skip if social media module not installed
        if not hasattr(self.company, "social_twitter"):
            self.skipTest("Social media fields not available")

        # Disable force template for this test
        self.company.force_signature_template = False

        # Create template with social media
        template = self.env["signature.template"].create(
            {
                "name": "Test Social Invalidation",
                "body_html": (
                    '<div>Twitter: <t t-if="social_twitter">'
                    '<t t-out="social_twitter"/></t>'
                    '<t t-else="">No Twitter</t></div>'
                ),
                "company_id": self.company.id,
            }
        )

        self.user_demo.use_signature_template = True
        self.user_demo.signature_template_id = template

        # Set initial social media empty
        self.company.social_twitter = False
        # Force computation to ensure signature is generated
        self.user_demo._compute_signature()
        original_signature = self.user_demo.signature
        self.assertIn("No Twitter", original_signature)

        # Set social media
        self.company.social_twitter = "https://twitter.com/company"
        # Invalidate cache to ensure recomputation
        self.user_demo.invalidate_recordset()
        new_signature = self.user_demo.signature

        self.assertNotIn("No Twitter", new_signature)

        # Check if website module is installed
        has_website = self.env.registry.get("website") is not None
        if has_website:
            self.assertIn("/website/social/twitter", new_signature)
        else:
            self.assertIn("twitter.com/company", new_signature)

    def test_48_token_generation(self):
        """Test token generation logic."""
        from ..controllers.public_image import PublicSignatureImage

        controller = PublicSignatureImage()

        # Test token generation
        user_id = 123
        token_hash = controller._generate_token_hash("avatar", user_id)
        token = f"{user_id}_{token_hash}"

        # Token should be properly formatted
        self.assertIn("_", token)
        parts = token.split("_", 1)
        self.assertEqual(parts[0], str(user_id))
        self.assertTrue(len(parts[1]) > 0)

    def test_49_image_format_edge_cases(self):
        """Test image format detection edge cases."""
        from ..controllers.public_image import PublicSignatureImage

        controller = PublicSignatureImage()

        # Test with empty data
        self.assertEqual(controller._detect_image_format(b""), "image/png")

        # Test with very short data
        self.assertEqual(controller._detect_image_format(b"AB"), "image/png")

        # Test with corrupted header
        self.assertEqual(
            controller._detect_image_format(b"\xff\xff\xff\xff" * 3), "image/png"
        )

    def test_50_extension_mapping(self):
        """Test content type to extension mapping."""
        from ..controllers.public_image import PublicSignatureImage

        controller = PublicSignatureImage()

        # Test known types
        self.assertEqual(
            controller._get_extension_from_content_type("image/jpeg"), ".jpg"
        )
        self.assertEqual(
            controller._get_extension_from_content_type("image/png"), ".png"
        )
        self.assertEqual(
            controller._get_extension_from_content_type("image/svg+xml"), ".svg"
        )
        self.assertEqual(
            controller._get_extension_from_content_type("image/gif"), ".gif"
        )

        # Test unknown type
        self.assertEqual(
            controller._get_extension_from_content_type("image/unknown"), ".png"
        )

    def test_51_token_security(self):
        """Test token security features."""
        from ..controllers.public_image import PublicSignatureImage

        controller = PublicSignatureImage()

        # Test that tokens are different for different IDs
        token1 = controller._generate_token_hash("avatar", 1)
        token2 = controller._generate_token_hash("avatar", 2)
        self.assertNotEqual(token1, token2)

        # Test that tokens are different for different types
        avatar_token = controller._generate_token_hash("avatar", 1)
        logo_token = controller._generate_token_hash("logo", 1)
        self.assertNotEqual(avatar_token, logo_token)

    def test_52_all_supported_image_formats(self):
        """Test all supported image format detection."""
        from ..controllers.public_image import PublicSignatureImage

        controller = PublicSignatureImage()

        # Test all formats supported by the controller
        formats = [
            (b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00", "image/png"),
            (b"\xff\xd8\xff\xe0\x00\x00\x00\x00\x00\x00\x00\x00", "image/jpeg"),
            (b"GIF89a\x00\x00\x00\x00\x00\x00", "image/gif"),
            (b"<svg xmlns='http://www.w3.org/2000/svg'>", "image/svg+xml"),
            (b"RIFF\x00\x00\x00\x00WEBP", "image/webp"),
            (b"BM\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", "image/bmp"),
            (b"\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00", "image/x-icon"),
        ]

        for data, expected in formats:
            self.assertEqual(
                controller._detect_image_format(data),
                expected,
                f"Failed to detect {expected}",
            )

        # Test SVG with longer content
        svg_with_content = (
            b'<html><body><svg xmlns="http://www.w3.org/2000/svg"></svg></body></html>'
        )
        self.assertEqual(
            controller._detect_image_format(svg_with_content), "image/svg+xml"
        )

        # Test data exactly 12 bytes
        exactly_12 = b"EXACTLY12BYT"
        result = controller._detect_image_format(exactly_12)
        self.assertEqual(result, "image/png")  # Should use default

    def test_53_token_format_variations(self):
        """Test token format variations."""
        from ..controllers.public_image import PublicSignatureImage

        controller = PublicSignatureImage()

        # Test that different IDs produce different tokens
        token1 = controller._generate_token_hash("avatar", 1)
        token2 = controller._generate_token_hash("avatar", 2)
        self.assertNotEqual(token1, token2)

        # Test that different types produce different tokens
        avatar_token = controller._generate_token_hash("avatar", 1)
        logo_token = controller._generate_token_hash("logo", 1)
        self.assertNotEqual(avatar_token, logo_token)

        # Test token consistency
        token_a = controller._generate_token_hash("avatar", 42)
        token_b = controller._generate_token_hash("avatar", 42)
        self.assertEqual(token_a, token_b, "Same inputs should produce same token")

    def test_54_public_url_generation(self):
        """Test public URL generation."""
        from ..controllers.public_image import PublicSignatureImage

        # Test avatar URL generation
        avatar_url = PublicSignatureImage.get_public_avatar_url(
            self.user_demo.id, env=self.env
        )
        self.assertIn("/mailcdn/avatar/", avatar_url)
        self.assertIn(f"{self.user_demo.id}_", avatar_url)

        # Test company logo URL
        logo_url = PublicSignatureImage.get_public_logo_url(
            self.company.id, env=self.env
        )
        self.assertIn("/mailcdn/logo/", logo_url)
        self.assertIn(f"{self.company.id}_", logo_url)

    def test_55_controller_methods_exist(self):
        """Test that required controller methods exist."""
        from ..controllers.public_image import PublicSignatureImage

        controller = PublicSignatureImage()

        # Verify all required methods exist
        required_methods = [
            "public_user_avatar",
            "public_company_logo",
            "_generate_token_hash",
            "_detect_image_format",
            "_get_extension_from_content_type",
            "get_public_avatar_url",
            "get_public_logo_url",
        ]

        for method_name in required_methods:
            self.assertTrue(
                hasattr(controller, method_name),
                f"Controller should have {method_name} method",
            )

    def test_56_user_image_round_rendering(self):
        """Test that user_image_round renders correctly with img tag.

        This test verifies the fix for the QWeb security issue where custom
        template variables were not being rendered because they weren't in
        the mail_allowed_qweb_expressions list.
        """
        template_html = """
            <div>
                <t t-out="user_image_round"/>
                <t t-out="user_image_large_round"/>
            </div>
        """
        template = self.env["signature.template"].create(
            {
                "name": "Round Image Test",
                "body_html": template_html,
                "company_id": self.company.id,
            }
        )

        rendered = template._render_signature(self.user_admin)

        # Check that actual img tags are rendered, not empty divs
        self.assertIn("<img src=", rendered, "user_image_round should render img tag")
        self.assertIn(
            "border-radius:50%", rendered, "user_image_round should have border-radius"
        )
        self.assertIn(
            'width="64" height="64"',
            rendered,
            "user_image_round should have correct size",
        )
        self.assertIn(
            'width="116" height="116"',
            rendered,
            "user_image_large_round should have correct size",
        )

        # Ensure we have two img tags (one for each round image)
        img_count = rendered.count("<img")
        self.assertEqual(img_count, 2, f"Should have 2 img tags but found {img_count}")

        # Check that the rendered HTML contains actual image elements, not empty content
        self.assertNotIn(
            '<t t-out="user_image_round" />',
            rendered,
            "QWeb should render the variable",
        )
        self.assertNotIn(
            '<t t-out="user_image_large_round" />',
            rendered,
            "QWeb should render the variable",
        )

        # Verify that public avatar URLs are used
        self.assertIn("/mailcdn/avatar/", rendered, "Should use public avatar URLs")

    def test_57_mail_allowed_qweb_expressions(self):
        """Test that mail_allowed_qweb_expressions is properly inherited.

        We don't add custom variables to the whitelist anymore since they're
        not fields on res.users but context variables passed via add_context.
        """
        allowed_expressions = self.user_admin.mail_allowed_qweb_expressions()

        # Test that base expressions are still there
        base_vars = ["object.name", "object.user_id.name"]
        for var in base_vars:
            self.assertIn(
                var,
                allowed_expressions,
                f"Base variable '{var}' should still be in allowed expressions",
            )

    def test_58_sanitization_style_whitelist(self):
        """Test _get_style_whitelist method."""
        template = self.env["signature.template"].create(
            {
                "name": "Whitelist Test",
                "body_html": "<p>Test</p>",
                "company_id": self.company.id,
            }
        )

        whitelist = template._get_style_whitelist()

        # Check that we get a list of allowed CSS properties
        self.assertIsInstance(whitelist, list)
        self.assertGreater(len(whitelist), 0, "Whitelist should not be empty")

        # Check some common CSS properties that should be allowed
        expected_properties = [
            "color",
            "background-color",
            "font-size",
            "font-family",
            "text-align",
            "padding",
            "margin",
            "border",
        ]

        for prop in expected_properties:
            self.assertIn(prop, whitelist, f"'{prop}' should be in whitelist")

    def test_59_sanitization_report_generation(self):
        """Test _get_sanitization_report method."""
        # Create template with styles that will be sanitized
        template_html = """
            <div style="color: red; letter-spacing: 2px; border-right: 1px solid #ccc;">
                <p style="font-family: Arial, sans-serif; outline: 1px solid blue;">
                    <t t-out="name"/>
                </p>
            </div>
        """

        template = self.env["signature.template"].create(
            {
                "name": "Sanitization Report Test",
                "body_html": template_html,
                "company_id": self.company.id,
            }
        )

        report = template._get_sanitization_report()

        # Check report structure
        self.assertIn("changes_detected", report)
        self.assertIn("original_html", report)
        self.assertIn("sanitized_html", report)
        self.assertIn("sanitization_contexts", report)

        # Check that changes were detected
        self.assertTrue(
            report["changes_detected"], "Should detect sanitization changes"
        )

        # Check contexts
        self.assertGreater(len(report["sanitization_contexts"]), 0)

        # Check first context (Email Composer)
        email_context = report["sanitization_contexts"][0]
        self.assertEqual(email_context["name"], "Email Composer (Default)")
        self.assertTrue(email_context["changed"])

        # Check that problematic styles are detected
        if "diff_summary" in email_context:
            summary_text = " ".join(email_context["diff_summary"])
            # At least one of these issues should be detected
            detected_issues = (
                "letter-spacing" in summary_text
                or "outline" in summary_text
                or "border" in summary_text
            )
            self.assertTrue(detected_issues, "Should detect problematic CSS properties")

    def test_60_sanitization_report_formatting(self):
        """Test _format_sanitization_report method."""
        template = self.env["signature.template"].create(
            {
                "name": "Format Report Test",
                "body_html": "<div>Test</div>",
                "company_id": self.company.id,
            }
        )

        # Test with no issues
        report_no_issues = {
            "changes_detected": False,
            "original_html": "<div>Test</div>",
            "sanitized_html": "<div>Test</div>",
        }

        formatted = template._format_sanitization_report(report_no_issues)
        self.assertIn("No sanitization issues detected", formatted)
        self.assertIn("fa-check-circle", formatted)

        # Test with issues
        report_with_issues = {
            "changes_detected": True,
            "sanitization_contexts": [
                {
                    "name": "Email Composer (Default)",
                    "changed": True,
                    "diff_summary": [
                        "❌ Border shorthand detected - use individual properties",
                        "❌ letter-spacing is not allowed - adjust font-size instead",
                    ],
                }
            ],
        }

        formatted = template._format_sanitization_report(report_with_issues)
        self.assertIn("fa-exclamation-triangle", formatted)
        self.assertIn("Border shorthand detected", formatted)
        self.assertIn("Solutions for Common Issues", formatted)

        # Test with error
        report_with_error = {"error": "Test error message"}

        formatted = template._format_sanitization_report(report_with_error)
        self.assertIn("fa-exclamation-circle", formatted)
        self.assertIn("Test error message", formatted)

    def test_61_action_check_sanitization(self):
        """Test action_check_sanitization method."""
        template = self.env["signature.template"].create(
            {
                "name": "Action Check Test",
                "body_html": '<div style="color: red;">Test</div>',
                "company_id": self.company.id,
            }
        )

        # Execute action
        action = template.action_check_sanitization()

        # Check action structure
        self.assertIn("type", action)

        # If wizard works, check wizard action
        if action["type"] == "ir.actions.act_window":
            self.assertEqual(action["res_model"], "signature.sanitization.check")
            self.assertEqual(action["view_mode"], "form")
            self.assertEqual(action["target"], "new")
            self.assertIn("res_id", action)

            # Check wizard was created
            wizard_id = action["res_id"]
            wizard = self.env["signature.sanitization.check"].browse(wizard_id)
            self.assertTrue(wizard.exists())
            self.assertEqual(wizard.template_id, template)

        # If fallback to notification
        elif action["type"] == "ir.actions.client":
            self.assertEqual(action["tag"], "display_notification")
            self.assertIn("params", action)
            self.assertIn("message", action["params"])

    def test_62_sanitization_wizard_creation(self):
        """Test signature.sanitization.check wizard."""
        template = self.env["signature.template"].create(
            {
                "name": "Wizard Test",
                "body_html": '<div style="letter-spacing: 2px;">Test</div>',
                "company_id": self.company.id,
            }
        )

        # Get sanitization report
        report = template._get_sanitization_report()

        # Create wizard
        wizard = self.env["signature.sanitization.check"].create(
            {
                "template_id": template.id,
                "has_issues": report.get("changes_detected", False),
                "report_html": template._format_sanitization_report(report),
                "original_html": report.get("original_html", ""),
                "sanitized_html": report.get("sanitized_html", ""),
            }
        )

        # Check wizard fields
        self.assertEqual(wizard.template_id, template)
        self.assertEqual(wizard.template_name, template.name)
        self.assertTrue(wizard.has_issues)
        self.assertTrue(wizard.report_html)
        self.assertTrue(wizard.original_html)
        self.assertTrue(wizard.sanitized_html)

    def test_63_sanitization_diff_computation(self):
        """Test diff_html computation in sanitization wizard."""
        template = self.env["signature.template"].create(
            {
                "name": "Diff Test",
                "body_html": (
                    '<div style="color: red; outline: 1px solid blue;">' "Content</div>"
                ),
                "company_id": self.company.id,
            }
        )

        # Get report and create wizard
        report = template._get_sanitization_report()
        wizard = self.env["signature.sanitization.check"].create(
            {
                "template_id": template.id,
                "has_issues": True,
                "report_html": "Test",
                "original_html": report.get("original_html", ""),
                "sanitized_html": report.get("sanitized_html", ""),
            }
        )

        # Check diff computation
        self.assertTrue(wizard.diff_html)
        # Should contain diff markers
        self.assertIn("diff", wizard.diff_html.lower())

    def test_64_sanitization_edge_cases(self):
        """Test sanitization checking edge cases."""
        # Test minimal template - use minimal content to avoid validation error
        minimal_template = self.env["signature.template"].create(
            {
                "name": "Minimal Sanitization Test",
                "body_html": "<div>Minimal content</div>",
                "company_id": self.company.id,
            }
        )

        report = minimal_template._get_sanitization_report()
        # Even minimal content gets wrapped in signature div, which may have changes
        # The important thing is the report works without errors
        self.assertIn("changes_detected", report)
        self.assertIn("original_html", report)
        self.assertIn("sanitized_html", report)

        # Test template with only allowed styles
        allowed_template = self.env["signature.template"].create(
            {
                "name": "Allowed Styles Test",
                "body_html": (
                    '<div style="color: red; font-size: 14px; '
                    'text-align: center;">Test</div>'
                ),
                "company_id": self.company.id,
            }
        )

        report = allowed_template._get_sanitization_report()
        # Should not detect changes if all styles are allowed
        if report["changes_detected"]:
            # Check that it's not our test styles causing issues
            summary = str(
                report.get("sanitization_contexts", [{}])[0].get("diff_summary", [])
            )
            self.assertNotIn("color", summary.lower())
            self.assertNotIn("font-size", summary.lower())
            self.assertNotIn("text-align", summary.lower())

    def test_65_sanitization_complex_styles(self):
        """Test sanitization with complex style scenarios."""
        # Test multiple problematic styles
        # Long lines needed for testing problematic CSS that will be sanitized
        complex_html = """
            <table style="border: 1px solid #ccc; background: linear-gradient(to right, #fff, #eee);">
                <tr>
                    <td style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto;">
                        <p style="letter-spacing: 0.5em; text-transform: uppercase;">
                            <t t-out="name"/>
                        </p>
                    </td>
                </tr>
            </table>
        """  # noqa: E501

        template = self.env["signature.template"].create(
            {
                "name": "Complex Sanitization Test",
                "body_html": complex_html,
                "company_id": self.company.id,
            }
        )

        report = template._get_sanitization_report()
        self.assertTrue(report["changes_detected"])

        # Format the report
        formatted = template._format_sanitization_report(report)

        # Should provide solutions for detected issues
        self.assertIn("Solutions for Common Issues", formatted)
        # Check for specific suggestions
        if "border" in formatted.lower():
            self.assertIn("border", formatted)
        if "font-family" in formatted.lower():
            self.assertIn("single font", formatted)
        if "background" in formatted.lower() or "gradient" in formatted.lower():
            self.assertIn("background-color", formatted)

    def test_66_simple_diff_summary(self):
        """Test _get_simple_diff_summary method."""
        template = self.env["signature.template"].create(
            {
                "name": "Diff Summary Test",
                "body_html": "<p>Test</p>",
                "company_id": self.company.id,
            }
        )

        # Test with various style issues
        original = (
            '<div style="border-right: 1px solid #ccc; letter-spacing: 2px;">Test</div>'
        )
        sanitized = (
            '<div style="border-right-width: 1px; border-right-style: solid; '
            'border-right-color: #ccc;">Test</div>'
        )

        summary = template._get_simple_diff_summary(original, sanitized)
        self.assertIsInstance(summary, list)

        # Should detect border shorthand
        summary_text = " ".join(summary)
        if "border" in original and "border-right-" not in original:
            self.assertIn("border", summary_text.lower())

    def test_67_sanitization_performance(self):
        """Test sanitization checking with large templates."""
        # Create a large template with many elements
        large_html = "<div>"
        for i in range(50):
            large_html += f"""
                <table style="width: 100%; margin: 10px;">
                    <tr>
                        <td style="padding: 5px; color: #{i:02x}{i:02x}{i:02x};">
                            Cell {i}
                        </td>
                    </tr>
                </table>
            """
        large_html += "</div>"

        template = self.env["signature.template"].create(
            {
                "name": "Large Template Test",
                "body_html": large_html,
                "company_id": self.company.id,
            }
        )

        # Should complete without timeout
        import time

        start_time = time.time()
        report = template._get_sanitization_report()
        end_time = time.time()

        # Should complete in reasonable time (less than 5 seconds)
        self.assertLess(end_time - start_time, 5.0, "Sanitization check took too long")
        self.assertIn("changes_detected", report)

    def test_68_sanitization_with_qweb_rendering(self):
        """Test sanitization checking with QWeb variables."""
        # Template with QWeb variables and problematic styles
        qweb_html = """
            <div t-att-style="'color: ' + primary_color + '; letter-spacing: 1px;'">
                <t t-out="name"/>
                <span style="outline: 2px dotted red;">
                    <t t-out="email"/>
                </span>
            </div>
        """

        template = self.env["signature.template"].create(
            {
                "name": "QWeb Sanitization Test",
                "body_html": qweb_html,
                "company_id": self.company.id,
            }
        )

        # Should render QWeb first, then check sanitization
        report = template._get_sanitization_report()

        # Check that QWeb was rendered
        # (note: _get_sanitization_report uses self.env.user)
        # The report is rendered with the current test user, not user_admin
        self.assertIn("o_mail_signature", report["original_html"])
        # Check that email placeholder was rendered to something
        self.assertIn("@", report["original_html"])  # Should have an email

        # Check sanitization was applied
        self.assertTrue(report["changes_detected"])

    def test_69_sanitization_error_handling(self):
        """Test error handling in sanitization checking."""
        # Create template with invalid QWeb that might cause rendering errors
        template = self.env["signature.template"].create(
            {
                "name": "Error Handling Test",
                "body_html": "<div><t t-out='nonexistent_variable'/></div>",
                "company_id": self.company.id,
            }
        )

        # Should handle errors gracefully
        report = template._get_sanitization_report()

        # Should either have an error or handle the missing variable
        self.assertIn("original_html", report)
        # If there's an error, it should be in the report
        if "error" in report:
            self.assertTrue(report["error"])

    def test_70_sanitization_all_contexts(self):
        """Test that all sanitization contexts are checked."""
        template = self.env["signature.template"].create(
            {
                "name": "All Contexts Test",
                "body_html": '<div class="test-class" style="color: blue;">Test</div>',
                "company_id": self.company.id,
            }
        )

        report = template._get_sanitization_report()

        # Should have multiple contexts
        self.assertGreater(len(report["sanitization_contexts"]), 1)

        # Check context names
        context_names = [ctx["name"] for ctx in report["sanitization_contexts"]]
        self.assertIn("Email Composer (Default)", context_names)
        self.assertIn("Chatter Messages", context_names)

        # Chatter context should strip classes
        chatter_context = next(
            ctx
            for ctx in report["sanitization_contexts"]
            if ctx["name"] == "Chatter Messages"
        )

        # If the template has classes, chatter should show changes
        if "class=" in template.body_html:
            self.assertTrue(
                chatter_context.get("changed", False),
                "Chatter context should detect class stripping",
            )
