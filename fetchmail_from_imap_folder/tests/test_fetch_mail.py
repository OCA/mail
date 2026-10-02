# Copyright - 2026 AlMax Solutions E.I.R.L. <https://almaxerp.com>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.mail.models.fetchmail import FetchmailServer as CoreFetchmailServer


class TestFetchMail(TransactionCase):
    """The folders must be fetched on every path that core uses to fetch mail."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cron = cls.env.ref("mail.ir_cron_mail_gateway_action")
        cls.FetchmailServer = cls.env["fetchmail.server"]
        # Servers that happen to be in the database must not be contacted.
        cls.FetchmailServer.search([]).write({"state": "draft"})
        cls.server = cls.FetchmailServer.create(
            {
                "name": "Test Fetchmail Server",
                "server": "imap.example.com",
                "server_type": "imap",
                "folders_only": True,
                "state": "done",
                "folder_ids": [
                    (
                        0,
                        0,
                        {
                            "path": "customers",
                            "model_id": cls.env.ref("base.model_res_partner").id,
                            "match_algorithm": "odoo_standard",
                            "state": "done",
                        },
                    )
                ],
            }
        )
        cls.folder = cls.server.folder_ids

    def _run(self, method):
        """Run method, return the folders fetched and the servers core did."""
        folders = self.env["fetchmail.server.folder"]
        servers = self.FetchmailServer

        def fetch_folder(folder_self):
            nonlocal folders
            folders |= folder_self

        def fetch_inbox(server_self, **kwargs):
            nonlocal servers
            servers |= server_self

        with (
            patch.object(self.folder.__class__, "fetch_mail", fetch_folder),
            patch.object(CoreFetchmailServer, "_fetch_mail", fetch_inbox),
        ):
            method()
        return folders, servers

    def _run_cron(self):
        FetchmailServer = self.FetchmailServer.with_context(
            cron_id=self.cron.id, cron_end_time=float("inf")
        )
        return self._run(FetchmailServer._fetch_mails)

    def test_cron_folders_only(self):
        """The cron fetches the folders, and leaves the inbox alone."""
        folders, servers = self._run_cron()
        self.assertEqual(folders, self.folder)
        self.assertFalse(servers)
        self.assertTrue(self.server.date)

    def test_cron_with_inbox(self):
        """Without folders_only the cron fetches both inbox and folders."""
        self.server.folders_only = False
        folders, servers = self._run_cron()
        self.assertEqual(folders, self.folder)
        self.assertEqual(servers, self.server)

    def test_button_folders_only(self):
        """The Fetch Now button fetches the folders, once."""
        folders, servers = self._run(self.server.fetch_mail)
        self.assertEqual(folders, self.folder)
        self.assertFalse(servers)

    def test_unconfirmed_server(self):
        """Folders of a server that is not confirmed are not fetched."""
        self.server.state = "draft"
        folders, servers = self._run(self.server.fetch_mail)
        self.assertFalse(folders)
        self.assertFalse(servers)
