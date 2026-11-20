# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests.common import TransactionCase


class MailGatewayTestCase(TransactionCase):
    # "abstract" maps to mail.gateway.abstract, which is always in the registry.
    # selection_add in test models runs after the registry is built and has no effect,
    # so we patch the field's selection list at test time instead.
    GATEWAY_TYPE = "abstract"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._patch_gateway_type()
        cls._patch_send()
        cls._setup_env()

    @classmethod
    def _patch_gateway_type(cls):
        """Temporarily add GATEWAY_TYPE to the gateway_type selection.

        Odoo 19 validates against field._selection (a dict), not field.selection
        (a list), so both attributes must be patched.
        """
        field = cls.env["mail.gateway"]._fields["gateway_type"]
        original_selection = field.selection
        original__selection = field._selection
        new_selection = list(original_selection or []) + [(cls.GATEWAY_TYPE, "Test")]
        field.selection = new_selection
        field._selection = dict(new_selection)
        cls.addClassCleanup(setattr, field, "selection", original_selection)
        cls.addClassCleanup(setattr, field, "_selection", original__selection)

    @classmethod
    def _patch_send(cls):
        """Make mail.gateway.abstract._send a no-op instead of NotImplementedError."""
        impl_cls = type(cls.env["mail.gateway.abstract"])
        patcher = patch.object(impl_cls, "_send", return_value=None)
        patcher.start()
        cls.addClassCleanup(patcher.stop)

    @classmethod
    def _setup_context(cls):
        return dict(
            cls.env.context, tracking_disable=True, test_queue_job_no_delay=True
        )

    @classmethod
    def _setup_env(cls):
        cls.env = cls.env(context=cls._setup_context())
