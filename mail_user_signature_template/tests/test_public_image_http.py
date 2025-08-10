# Copyright 2025 OCA Contributors
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import logging
import urllib.parse
from io import BytesIO

from PIL import Image

from odoo.tests import HttpCase, tagged

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestPublicImageHttp(HttpCase):
    """Test public image HTTP routes directly."""

    def test_00_route_exists(self):
        """Test if mailcdn routes are registered."""
        # Test with invalid token - should still hit the route and return 404
        response = self.url_open("/mailcdn/avatar/invalid_token.png")
        _logger.info(f"Route test response: {response.status_code}")
        # If route doesn't exist, we'd get a different error
        self.assertEqual(response.status_code, 404)

    def test_01_public_user_avatar_valid(self):
        """Test public user avatar with valid token."""
        from ..controllers.public_image import PublicSignatureImage

        # Use user ID 2 which should be OdooBot or similar system user
        existing_user = self.env["res.users"].browse(2)
        if not existing_user.exists():
            # Fallback to any existing user
            existing_user = self.env["res.users"].search([], limit=1)

        # Add avatar to the user
        test_image = Image.new("RGB", (100, 100), color="red")
        buffer = BytesIO()
        test_image.save(buffer, format="PNG")
        existing_user.avatar_128 = base64.b64encode(buffer.getvalue())

        # Use the class method to get the URL with proper token
        avatar_url = PublicSignatureImage.get_public_avatar_url(
            existing_user.id, size="128", env=self.env
        )
        # Extract just the path from the full URL
        url_parts = urllib.parse.urlparse(avatar_url)
        url = url_parts.path
        if url_parts.query:
            url += f"?{url_parts.query}"

        _logger.info(f"Testing URL: {url} with base_url: {self.base_url()}")

        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Content-Type"), "image/png")
        self.assertIn("Cache-Control", response.headers)
        self.assertIn("ETag", response.headers)

        # Verify it's an actual image
        image = Image.open(BytesIO(response.content))
        self.assertEqual(image.format, "PNG")

    def test_02_public_user_avatar_invalid_token(self):
        """Test public user avatar with invalid token."""
        # Invalid token format
        response = self.url_open("/mailcdn/avatar/invalid_token.png")
        self.assertEqual(response.status_code, 404)

        # Invalid hash - use existing user ID
        existing_user = self.env["res.users"].search([], limit=1)
        response = self.url_open(f"/mailcdn/avatar/{existing_user.id}_wronghash.png")
        self.assertEqual(response.status_code, 404)

        # Non-existent user
        response = self.url_open("/mailcdn/avatar/99999_somehash.png")
        self.assertEqual(response.status_code, 404)

    def test_03_public_user_avatar_no_image(self):
        """Test public user avatar when user has no image."""
        # Find a user without avatar or clear one
        existing_user = self.env["res.users"].search(
            [("avatar_128", "=", False)], limit=1
        )
        if not existing_user:
            existing_user = self.env["res.users"].search([], limit=1)
            existing_user.avatar_128 = False

        from ..controllers.public_image import PublicSignatureImage

        avatar_url = PublicSignatureImage.get_public_avatar_url(
            existing_user.id, env=self.env
        )
        url_parts = urllib.parse.urlparse(avatar_url)
        url = url_parts.path
        if url_parts.query:
            url += f"?{url_parts.query}"

        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Content-Type"), "image/png")
        # Should return default avatar
        self.assertIn("Cache-Control", response.headers)

    def test_04_public_user_avatar_different_sizes(self):
        """Test avatar with different size parameters."""
        from ..controllers.public_image import PublicSignatureImage

        # Use existing user with avatar
        existing_user = self.env["res.users"].browse(2)
        if not existing_user.avatar_128:
            test_image = Image.new("RGB", (100, 100), color="blue")
            buffer = BytesIO()
            test_image.save(buffer, format="PNG")
            existing_user.avatar_128 = base64.b64encode(buffer.getvalue())

        # Test different sizes
        for size in ["128", "256", "512"]:
            avatar_url = PublicSignatureImage.get_public_avatar_url(
                existing_user.id, size=size, env=self.env
            )
            url_parts = urllib.parse.urlparse(avatar_url)
            url = url_parts.path
            if url_parts.query:
                url += f"?{url_parts.query}"

            response = self.url_open(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers.get("Content-Type"), "image/png")

    def test_05_public_company_logo_valid(self):
        """Test public company logo with valid token."""
        from ..controllers.public_image import PublicSignatureImage

        # Use main company (ID 1) which should always exist
        existing_company = self.env["res.company"].browse(1)
        # Always set a PNG logo to ensure consistent test
        logo_image = Image.new("RGB", (200, 100), color="blue")
        buffer = BytesIO()
        logo_image.save(buffer, format="PNG")
        existing_company.partner_id.image_256 = base64.b64encode(buffer.getvalue())

        logo_url = PublicSignatureImage.get_public_logo_url(
            existing_company.id, env=self.env
        )
        url_parts = urllib.parse.urlparse(logo_url)
        url = url_parts.path

        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Content-Type"), "image/png")
        self.assertIn("Cache-Control", response.headers)
        # Should have 30 days cache
        self.assertIn("max-age=2592000", response.headers.get("Cache-Control"))

        # Verify it's an actual image
        image = Image.open(BytesIO(response.content))
        self.assertEqual(image.format, "PNG")

    def test_06_public_company_logo_external_url(self):
        """Test company logo with external URL redirect."""
        from ..controllers.public_image import PublicSignatureImage

        # Use main company (ID 1) and set external URL
        existing_company = self.env["res.company"].browse(1)
        # Clear any existing logo to ensure redirect works
        existing_company.partner_id.image_256 = False
        existing_company.signature_logo_url = "https://example.com/logo.png"

        logo_url = PublicSignatureImage.get_public_logo_url(
            existing_company.id, env=self.env
        )
        url_parts = urllib.parse.urlparse(logo_url)
        url = url_parts.path

        # Should redirect to external URL
        response = self.url_open(url, allow_redirects=False)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response.headers.get("Location"), "https://example.com/logo.png"
        )

    def test_07_public_company_logo_no_image(self):
        """Test company logo when company has no logo."""
        from ..controllers.public_image import PublicSignatureImage

        # Use main company and ensure no logo or external URL
        existing_company = self.env["res.company"].browse(1)
        existing_company.partner_id.image_256 = False
        existing_company.signature_logo_url = False

        logo_url = PublicSignatureImage.get_public_logo_url(
            existing_company.id, env=self.env
        )
        url_parts = urllib.parse.urlparse(logo_url)
        url = url_parts.path

        response = self.url_open(url)
        self.assertEqual(response.status_code, 404)

    def test_08_public_image_different_formats(self):
        """Test that routes accept different image format extensions."""
        from ..controllers.public_image import PublicSignatureImage

        # Use existing user with avatar
        existing_user = self.env["res.users"].browse(2)
        if not existing_user.avatar_128:
            test_image = Image.new("RGB", (100, 100), color="green")
            buffer = BytesIO()
            test_image.save(buffer, format="PNG")
            existing_user.avatar_128 = base64.b64encode(buffer.getvalue())

        # Get base URL without extension
        avatar_url = PublicSignatureImage.get_public_avatar_url(
            existing_user.id, env=self.env
        )
        url_parts = urllib.parse.urlparse(avatar_url)
        base_path = url_parts.path.rsplit(".", 1)[0]  # Remove extension

        # Test different format extensions
        extensions = [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"]
        extensions.extend([".ico", ""])
        for ext in extensions:
            url = f"{base_path}{ext}"
            if url_parts.query:
                url += f"?{url_parts.query}"
            response = self.url_open(url)
            self.assertEqual(response.status_code, 200)
            # All should return the same PNG image since that's what we stored
            self.assertEqual(response.headers.get("Content-Type"), "image/png")

    def test_09_public_image_svg_format(self):
        """Test SVG image format detection."""
        from ..controllers.public_image import PublicSignatureImage

        # Use existing user and set SVG avatar
        existing_user = self.env["res.users"].browse(3)
        if not existing_user.exists():
            existing_user = self.env["res.users"].browse(2)

        # Simple SVG content
        svg_content = (
            b'<svg xmlns="http://www.w3.org/2000/svg" '
            b'width="100" height="100">'
            b'<rect width="100" height="100" fill="red"/></svg>'
        )
        existing_user.avatar_128 = base64.b64encode(svg_content)

        avatar_url = PublicSignatureImage.get_public_avatar_url(
            existing_user.id, env=self.env
        )
        url_parts = urllib.parse.urlparse(avatar_url)
        # Change extension to .svg
        svg_url = url_parts.path.rsplit(".", 1)[0] + ".svg"
        if url_parts.query:
            svg_url += f"?{url_parts.query}"

        response = self.url_open(svg_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Content-Type"), "image/svg+xml")

    def test_10_url_generation_methods(self):
        """Test the class methods for URL generation."""
        from ..controllers.public_image import PublicSignatureImage

        # Test avatar URL generation
        existing_user = self.env["res.users"].browse(2)
        avatar_url = PublicSignatureImage.get_public_avatar_url(
            existing_user.id, size="256", env=self.env
        )
        self.assertIn("/mailcdn/avatar/", avatar_url)
        self.assertIn(f"{existing_user.id}_", avatar_url)
        self.assertIn("size=256", avatar_url)

        # Test logo URL generation
        existing_company = self.env["res.company"].browse(1)
        logo_url = PublicSignatureImage.get_public_logo_url(
            existing_company.id, env=self.env
        )
        self.assertIn("/mailcdn/logo/", logo_url)
        self.assertIn(f"{existing_company.id}_", logo_url)

        # Test with user that has different image formats
        gif_user = self.env["res.users"].create(
            {
                "name": "GIF User",
                "login": "gif_user",
                "email": "gif@example.com",
            }
        )
        # Create a simple GIF
        gif_user.avatar_128 = base64.b64encode(b"GIF89a\x01\x00\x01\x00\x00\x00\x00")

        avatar_url = PublicSignatureImage.get_public_avatar_url(
            gif_user.id, env=self.env
        )
        self.assertIn(".gif", avatar_url)

    def test_11_corrupted_image_data(self):
        """Test handling of corrupted image data."""
        from ..controllers.public_image import PublicSignatureImage

        # Get third user
        existing_user = self.env["res.users"].search([], limit=1, offset=2)
        if not existing_user:
            existing_user = self.env["res.users"].browse(2)

        # Set corrupted base64 data
        existing_user.avatar_128 = "invalid_base64_data!!!"

        # URL generation should handle corrupted data gracefully
        avatar_url = PublicSignatureImage.get_public_avatar_url(
            existing_user.id, env=self.env
        )
        # Should fallback to .png extension
        self.assertIn(".png", avatar_url)
