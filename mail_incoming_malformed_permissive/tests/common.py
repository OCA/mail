# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tools import file_open


def read_eml(filename, mode="r"):
    """Return the content of ``<this module>/tests/eml/<filename>``."""
    path = f"mail_incoming_malformed_permissive/tests/eml/{filename}"
    with file_open(path, mode) as eml:
        return eml.read()
