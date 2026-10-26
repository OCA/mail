# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import smtplib
import ssl
from socket import gaierror, timeout

import idna
from OpenSSL.SSL import Error as SSLError

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import human_size

_logger = logging.getLogger(__name__)


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    max_email_size = fields.Float(string="Max Email Size")

    def _get_max_email_size(self):
        if self.max_email_size:
            return self.max_email_size
        return float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("base.default_max_email_size", "10")
        )

    def test_smtp_connection(self, autodetect_max_email_size=False):
        """Test the connection and if autodetect_max_email_size, set auto-detected max email size.

        :param bool autodetect_max_email_size: whether to autodetect the max email size
        :return (dict): client action to notify the user of the result of the operation (connection test or
        auto-detection successful depending on the autodetect_max_email_size parameter)

        :raises UserError: if the connection fails and if autodetect_max_email_size and
            the server doesn't support the auto-detection of email max size
        """
        for server in self:
            smtp = False
            try:
                smtp = self.connect(mail_server_id=server.id, allow_archived=True)
                # simulate sending an email from current user's address - without sending it!
                email_from = server._get_test_email_from()
                email_to = server._get_test_email_to()
                # Testing the MAIL FROM step should detect sender filter problems
                (code, repl) = smtp.mail(email_from)
                if code != 250:
                    raise UserError(
                        _(
                            "The server refused the sender address (%(email_from)s) with error %(repl)s",
                            email_from=email_from,
                            repl=repl,
                        )
                    )  # noqa: TRY301
                # Testing the RCPT TO step should detect most relaying problems
                (code, repl) = smtp.rcpt(email_to)
                if code not in (250, 251):
                    raise UserError(
                        _(
                            "The server refused the test recipient (%(email_to)s) with error %(repl)s",
                            email_to=email_to,
                            repl=repl,
                        )
                    )  # noqa: TRY301
                # Beginning the DATA step should detect some deferred rejections
                # Can't use self.data() as it would actually send the mail!
                smtp.putcmd("data")
                (code, repl) = smtp.getreply()
                if code != 354:
                    raise UserError(
                        _(
                            "The server refused the test connection with error %(repl)s",
                            repl=repl,
                        )
                    )  # noqa: TRY301
                if autodetect_max_email_size:
                    max_size = smtp.esmtp_features.get("size")
                    if not max_size:
                        raise UserError(
                            _(
                                'The server "%(server_name)s" doesn\'t return the maximum email size.',
                                server_name=server.name,
                            )
                        )
                    server.max_email_size = float(max_size) / (1024**2)
            except (UnicodeError, idna.core.InvalidCodepoint) as e:
                raise UserError(_("Invalid server name!\n %s", e)) from e
            except (gaierror, timeout) as e:
                raise UserError(
                    _(
                        "No response received. Check server address and port number.\n %s",
                        e,
                    )
                ) from e
            except smtplib.SMTPServerDisconnected as e:
                raise UserError(
                    _(
                        "The server has closed the connection unexpectedly. Check configuration served on this port number.\n %s",
                        e,
                    )
                ) from e
            except smtplib.SMTPResponseException as e:
                raise UserError(
                    _("Server replied with following exception:\n %s", e)
                ) from e
            except smtplib.SMTPNotSupportedError as e:
                raise UserError(
                    _("An option is not supported by the server:\n %s", e)
                ) from e
            except smtplib.SMTPException as e:
                raise UserError(
                    _(
                        "An SMTP exception occurred. Check port number and connection security type.\n %s",
                        e,
                    )
                ) from e
            except (ssl.SSLError, SSLError) as e:
                raise UserError(
                    _(
                        "An SSL exception occurred. Check connection security type.\n %s",
                        e,
                    )
                ) from e
            except UserError:
                raise
            except Exception as e:
                _logger.warning(
                    "Connection test on %s failed with a generic error.",
                    server,
                    exc_info=True,
                )
                raise UserError(
                    _("Connection Test Failed! Here is what we got instead:\n %s", e)
                ) from e
            finally:
                try:
                    if smtp:
                        smtp.close()
                except Exception:
                    # ignored, just a consequence of the previous exception
                    pass

        if autodetect_max_email_size:
            message = _(
                "Email maximum size updated (%(details)s).",
                details=", ".join(
                    f"{server.name}: {human_size(server.max_email_size * 1024 ** 2)}"
                    for server in self
                ),
            )
        else:
            message = _("Connection Test Successful!")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": message,
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},  # force a form reload
            },
        }

    def action_retrieve_max_email_size(self):
        self.ensure_one()
        return self.test_smtp_connection(autodetect_max_email_size=True)
