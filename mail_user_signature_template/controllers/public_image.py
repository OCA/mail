# Copyright 2025 OCA Contributors
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import hashlib
import hmac
import logging

from odoo import http
from odoo.http import Response, request
from odoo.tools import config

_logger = logging.getLogger(__name__)


class PublicSignatureImage(http.Controller):
    """Public endpoints for signature images that work with Gmail's proxy."""

    @http.route(
        [
            "/mailcdn/avatar/<string:token>.png",
            "/mailcdn/avatar/<string:token>.jpg",
            "/mailcdn/avatar/<string:token>.jpeg",
            "/mailcdn/avatar/<string:token>.gif",
            "/mailcdn/avatar/<string:token>.svg",
            "/mailcdn/avatar/<string:token>.webp",
            "/mailcdn/avatar/<string:token>.bmp",
            "/mailcdn/avatar/<string:token>.ico",
            "/mailcdn/avatar/<string:token>",
        ],
        type="http",
        auth="public",
        csrf=False,
        sitemap=False,
    )
    def public_user_avatar(self, token, size="128", **kw):
        """
        Serves user avatar images publicly for email signatures.
        Token format: userid_hash where hash validates the user ID.
        """
        try:
            user_id, provided_hash = token.split("_", 1)
            user_id = int(user_id)
        except (ValueError, AttributeError):
            return Response(status=404)

        # Validate token
        expected_hash = self._generate_token_hash("avatar", user_id)
        if not hmac.compare_digest(provided_hash, expected_hash):
            return Response(status=404)

        # Get user avatar
        user = request.env["res.users"].sudo().browse(user_id)
        if not user.exists():
            return Response(status=404)

        # Determine which field to use based on size
        size_map = {
            "128": "avatar_128",
            "256": "avatar_256",
            "512": "avatar_512",
        }
        field_name = size_map.get(size, "avatar_128")

        image_data = user[field_name]
        if not image_data:
            # Return default avatar if no image
            return self._get_default_avatar()

        raw = base64.b64decode(image_data)

        # Detect image format
        content_type = self._detect_image_format(raw)

        headers = [
            ("Content-Type", content_type),
            ("Content-Length", str(len(raw))),
            ("Cache-Control", "public, max-age=604800"),  # 7 days
            ("ETag", f'"{hashlib.md5(raw).hexdigest()}"'),
        ]
        return Response(raw, headers=headers)

    @http.route(
        [
            "/mailcdn/logo/<string:token>.png",
            "/mailcdn/logo/<string:token>.jpg",
            "/mailcdn/logo/<string:token>.jpeg",
            "/mailcdn/logo/<string:token>.gif",
            "/mailcdn/logo/<string:token>.svg",
            "/mailcdn/logo/<string:token>.webp",
            "/mailcdn/logo/<string:token>.bmp",
            "/mailcdn/logo/<string:token>.ico",
            "/mailcdn/logo/<string:token>",
        ],
        type="http",
        auth="public",
        csrf=False,
        sitemap=False,
    )
    def public_company_logo(self, token, **kw):
        """
        Serves company logo images publicly for email signatures.
        Token format: companyid_hash where hash validates the company ID.
        """
        try:
            company_id, provided_hash = token.split("_", 1)
            company_id = int(company_id)
        except (ValueError, AttributeError):
            return Response(status=404)

        # Validate token
        expected_hash = self._generate_token_hash("logo", company_id)
        if not hmac.compare_digest(provided_hash, expected_hash):
            return Response(status=404)

        # Get company logo
        company = request.env["res.company"].sudo().browse(company_id)
        if not company.exists():
            return Response(status=404)

        # Check for external logo URL first
        if company.signature_logo_url:
            # Redirect to external URL
            return request.redirect(company.signature_logo_url, code=301)

        # Use company logo from res.partner
        partner = company.partner_id
        if not partner or not partner.image_256:
            return Response(status=404)

        raw = base64.b64decode(partner.image_256)

        # Detect image format
        content_type = self._detect_image_format(raw)

        headers = [
            ("Content-Type", content_type),
            ("Content-Length", str(len(raw))),
            ("Cache-Control", "public, max-age=2592000"),  # 30 days for logos
            ("ETag", f'"{hashlib.md5(raw).hexdigest()}"'),
        ]
        return Response(raw, headers=headers)

    def _generate_token_hash(self, prefix, record_id):
        """Generate a secure hash for the token."""
        # Use database UUID as secret, fallback to db name
        # When called from controller, use request.env
        # When called from model, we'll pass the db name directly
        if hasattr(self, "env") and hasattr(self.env, "cr"):
            secret = config.get("database.uuid", self.env.cr.dbname)
        elif request and hasattr(request, "env"):
            secret = config.get("database.uuid", request.env.cr.dbname)
        else:
            # Fallback to a static secret from config
            secret = config.get("database.uuid", "odoo")

        message = f"{prefix}:{record_id}:{secret}"
        return hashlib.sha256(message.encode()).hexdigest()[:16]

    def _detect_image_format(self, data):
        """Detect image format from binary data.

        Based on Odoo's image format detection in:
        - odoo/tools/mimetypes.py (lines 123-144) for MIME type mappings
        - odoo/addons/base/models/ir_attachment.py for supported formats

        Odoo supports: PNG, JPEG, GIF, BMP, SVG, WebP, ICO, TIFF
        Auto-resize formats (default): png,jpeg,bmp,tiff
        """
        if len(data) < 12:
            return "image/png"  # Default fallback

        # Check for SVG (XML or SVG tags)
        # Reference: odoo/tools/mimetypes.py - SVG is restricted to system users
        if data[:5] == b"<?xml" or data[:4] == b"<svg" or b"<svg" in data[:1000]:
            return "image/svg+xml"
        # Check for PNG - Magic: b'\x89PNG\r\n\x1A\n'
        # Reference: odoo/tools/mimetypes.py line 126
        elif data[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        # Check for JPEG - Multiple magic bytes supported
        # Reference: odoo/tools/mimetypes.py lines 128-132
        elif data[:3] == b"\xff\xd8\xff":
            return "image/jpeg"
        # Check for GIF - Magic: GIF87a or GIF89a
        # Reference: odoo/tools/mimetypes.py line 127
        elif data[:6] in (b"GIF87a", b"GIF89a"):
            return "image/gif"
        # Check for WebP - Magic: RIFF....WEBP
        # Reference: odoo/tools/mimetypes.py line 133
        elif data[:4] == b"RIFF" and len(data) >= 12 and data[8:12] == b"WEBP":
            return "image/webp"
        # Check for BMP - Magic: BM
        # Reference: odoo/tools/mimetypes.py line 134
        elif data[:2] == b"BM":
            return "image/bmp"
        # Check for ICO - Magic: \x00\x00\x01\x00
        # Reference: odoo/tools/mimetypes.py line 140
        elif data[:4] == b"\x00\x00\x01\x00":
            return "image/x-icon"
        # Default to PNG for unknown formats
        return "image/png"

    def _get_default_avatar(self):
        """Return a default avatar image."""
        # Simple 1x1 transparent PNG
        transparent_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        )
        headers = [
            ("Content-Type", "image/png"),
            ("Content-Length", str(len(transparent_png))),
            ("Cache-Control", "public, max-age=86400"),
        ]
        return Response(transparent_png, headers=headers)

    @classmethod
    def _get_image_url_with_extension(
        cls, base_url, path_prefix, token, image_data, query_params=None
    ):
        """Generate URL with proper extension based on image format.

        Args:
            base_url: The base URL
            path_prefix: Path prefix (e.g., '/mailcdn/avatar/')
            token: Security token
            image_data: Base64 encoded image data
            query_params: Optional query parameters

        Returns:
            Full URL with detected extension
        """
        controller = cls()
        ext = ".png"  # Default extension

        if image_data:
            try:
                raw = base64.b64decode(image_data)
                content_type = controller._detect_image_format(raw)
                ext = cls._get_extension_from_content_type(content_type)
            except Exception as e:
                _logger.debug("Failed to detect image format: %s", e)

        url = f"{base_url}{path_prefix}{token}{ext}"
        if query_params:
            url += f"?{query_params}"
        return url

    @classmethod
    def get_public_avatar_url(cls, user_id, size="128", env=None):
        """Generate public URL for user avatar."""
        if env is None:
            env = request.env
        controller = cls()
        token_hash = controller._generate_token_hash("avatar", user_id)
        token = f"{user_id}_{token_hash}"
        base_url = env["ir.config_parameter"].sudo().get_param("web.base.url")

        # Get avatar data
        user = env["res.users"].sudo().browse(user_id)
        image_data = False
        if user.exists():
            size_map = {"128": "avatar_128", "256": "avatar_256", "512": "avatar_512"}
            field_name = size_map.get(size, "avatar_128")
            image_data = user[field_name]

        return cls._get_image_url_with_extension(
            base_url, "/mailcdn/avatar/", token, image_data, f"size={size}"
        )

    @classmethod
    def get_public_logo_url(cls, company_id, env=None):
        """Generate public URL for company logo."""
        if env is None:
            env = request.env
        controller = cls()
        token_hash = controller._generate_token_hash("logo", company_id)
        token = f"{company_id}_{token_hash}"
        base_url = env["ir.config_parameter"].sudo().get_param("web.base.url")

        # Get logo data
        company = env["res.company"].sudo().browse(company_id)
        image_data = False
        if company.exists():
            image_data = company.partner_id.image_256

        return cls._get_image_url_with_extension(
            base_url, "/mailcdn/logo/", token, image_data
        )

    @classmethod
    def _get_extension_from_content_type(cls, content_type):
        """Convert content type to file extension."""
        extension_map = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/gif": ".gif",
            "image/svg+xml": ".svg",
            "image/webp": ".webp",
            "image/bmp": ".bmp",
            "image/x-icon": ".ico",
        }
        return extension_map.get(content_type, ".png")
