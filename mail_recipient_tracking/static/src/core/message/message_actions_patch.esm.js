import {_t} from "@web/core/l10n/translation";
import {registerMessageAction} from "@mail/core/common/message_actions";

/** "Set as Reviewed" in the actions of the items of the messaging menu "Failed" tab */
registerMessageAction("mail-tracking-set-reviewed", {
    condition: ({message, owner}) =>
        owner.env.inMessagingMenu && message.is_failed_message,
    icon: "check",
    name: _t("Set as Reviewed"),
    onSelected: ({message}) => message.setMailTrackingReviewed(),
    sequence: 30,
});

/** "Retry" in the actions of the items of the messaging menu "Failed" tab */
registerMessageAction("mail-tracking-retry", {
    condition: ({message, owner}) =>
        owner.env.inMessagingMenu &&
        message.is_failed_message &&
        message.can_retry_failed_mails,
    icon: "send",
    name: _t("Retry"),
    onSelected: ({message}) => message.retryMailTrackingFailedMails(),
    sequence: 31,
});
