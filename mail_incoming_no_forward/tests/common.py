# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tools import file_open


def read_eml(filename, mode="r"):
    """Return the content of ``mail_incoming_no_forward/tests/eml/<filename>``."""
    with file_open(f"mail_incoming_no_forward/tests/eml/{filename}", mode) as eml:
        return eml.read()
