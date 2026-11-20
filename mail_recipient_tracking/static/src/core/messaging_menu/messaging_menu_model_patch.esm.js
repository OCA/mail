import {
    MENU_TABS,
    MessagingMenu,
} from "@mail/core/public_web/messaging_menu/messaging_menu_model";
import {_t} from "@web/core/l10n/translation";
import {fields} from "@mail/model/export";
import {patch} from "@web/core/utils/patch";

MENU_TABS.FAILED = "failed";

/**
 * Failed messages of the current user (see `mail.message.is_failed_message`).
 * Replaces the former "Failed" mailbox of the Discuss app. The server side domain
 * is defined in `MailTrackingMessagingMenuController._get_menu_tab_domain`.
 */
patch(MessagingMenu.prototype, {
    setup() {
        super.setup(...arguments);
        this.failedTab = fields.One("MessagingMenuTab", {
            compute() {
                if (this.store.self_user?.share !== false) {
                    return;
                }
                return {
                    id: MENU_TABS.FAILED,
                    recordType: "mail.message",
                    includesMessage: (message) => message.is_failed_message,
                    icon: "warning",
                    activeIcon: "warning",
                    iconClass: "text-danger",
                    sequence: 130,
                    label: _t("Failed"),
                    hideWhenZeroCounter: true,
                    emptyState: {
                        title: _t("No failed messages"),
                        subtitle: _t(
                            "Messages that could not be delivered will appear here."
                        ),
                    },
                };
            },
            eager: true,
        });
    },
});
