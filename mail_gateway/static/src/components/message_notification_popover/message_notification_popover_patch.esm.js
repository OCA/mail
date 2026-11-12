import {MessageNotificationPopover} from "@mail/core/common/message_notification_popover";
import {patch} from "@web/core/utils/patch";

patch(MessageNotificationPopover.prototype, {
    get recipientsData() {
        const gatewayNotifications = this.props.message.notification_ids.filter(
            (notification) => notification.isGateway
        );
        if (!gatewayNotifications.length) {
            return super.recipientsData;
        }
        // Gateway notifications have neither partner nor email: core lists them as
        // empty recipients. Show the gateway channel and its status instead.
        return [
            ...super.recipientsData.filter(
                (recipient) =>
                    recipient.name || recipient.email || recipient.notification
            ),
            ...gatewayNotifications.map((notification) => ({
                name: notification.gatewayChannelName,
                failure: notification.isFailure && notification.failureMessage,
                notification,
            })),
        ];
    },
});
