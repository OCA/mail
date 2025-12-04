import logging

_logger = logging.getLogger(__name__)

_rename_xmlids = {
    "mail_activity_board.group_show_mail_activity_board": "mail_activity_dashboard.group_show_mail_activity_board",  # noqa: E501
    "mail_activity_board.open_boards_activities": "mail_activity_dashboard.open_boards_activities",  # noqa: E501
    "mail_activity_board.board_menu_activities": "mail_activity_dashboard.board_menu_activities",  # noqa: E501
}


def install_module(cr, module_name):
    cr.execute(
        """
        UPDATE ir_module_module
        SET state = 'to install'
        WHERE name = %s AND state != 'installed'
        """,
        (module_name,),
    )


def rename_xmlid(cr, old, new):
    cr.execute(
        """
        UPDATE ir_model_data
        SET module = %s, name = %s
        WHERE module = %s and name = %s
        """,
        tuple(new.split(".") + old.split(".")),
    )


def migrate(cr, version):
    _logger.info("Start odoo pre-migration script for version %s", version)

    for old, into in _rename_xmlids.items():
        _logger.info("Rename xmlid %s into %s", old, into)
        rename_xmlid(cr, old, into)

    install_module(cr, "mail_activity_dashboard")
