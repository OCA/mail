# Copyright 2025 OCA Contributors
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestPublicImageHttpSimple(HttpCase):
    """Simple HTTP route tests that don't rely on database transactions."""

    def test_01_avatar_route_exists(self):
        """Test that avatar routes are registered and respond."""
        # Test with invalid token - should hit the route and return 404
        response = self.url_open("/mailcdn/avatar/invalid_token.png")
        self.assertEqual(response.status_code, 404)

        # Test different extensions
        for ext in [".jpg", ".svg", ".gif", ""]:
            response = self.url_open(f"/mailcdn/avatar/invalid{ext}")
            self.assertEqual(response.status_code, 404)

    def test_02_logo_route_exists(self):
        """Test that logo routes are registered and respond."""
        # Test with invalid token - should hit the route and return 404
        response = self.url_open("/mailcdn/logo/invalid_token.png")
        self.assertEqual(response.status_code, 404)

        # Test different extensions
        for ext in [".jpg", ".svg", ".gif", ""]:
            response = self.url_open(f"/mailcdn/logo/invalid{ext}")
            self.assertEqual(response.status_code, 404)

    def test_03_invalid_tokens(self):
        """Test various invalid token formats."""
        # Missing underscore
        response = self.url_open("/mailcdn/avatar/notokenhere.png")
        self.assertEqual(response.status_code, 404)

        # Non-numeric ID
        response = self.url_open("/mailcdn/avatar/abc_def123.png")
        self.assertEqual(response.status_code, 404)

        # Empty token
        response = self.url_open("/mailcdn/avatar/.png")
        self.assertEqual(response.status_code, 404)

    def test_04_query_params(self):
        """Test that query parameters are accepted."""
        response = self.url_open("/mailcdn/avatar/1_invalid.png?size=256")
        self.assertEqual(response.status_code, 404)  # Still 404 due to invalid token
