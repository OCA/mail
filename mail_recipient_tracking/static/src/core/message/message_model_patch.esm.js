import {Message} from "@mail/core/common/message_model";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

/** Tracking statuses (see `mail.message._tracking_status_map_get`) considered failed */
export const FAILED_TRACKING_STATES = [
    "error",
    "rejected",
    "spam",
    "bounced",
    "soft-bounced",
];

/**
 * @param {import("models").Message} message
 * @returns {Object[]} partner trackings of the message in a failed state
 */
export function getFailedRecipients(message) {
    return (message.partner_trackings ?? []).filter((tracking) =>
        FAILED_TRACKING_STATES.includes(tracking.status)
    );
}

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {Object[]} tracking status of each recipient, see `tracking_status()` */
        this.partner_trackings = [];
        this.mail_tracking_needs_action = false;
        this.is_failed_message = false;
        /** Whether the failed emails of the message can be queued again */
        this.can_retry_failed_mails = false;
    },

    /** Mark the failed message as reviewed, so it leaves the failed lists */
    async setMailTrackingReviewed() {
        await this.store.env.services.orm.call("mail.message", "set_need_action_done", [
            [this.id],
        ]);
        // The server also notifies the change through the bus, but update the
        // message right away so it leaves the failed lists without waiting.
        this.mail_tracking_needs_action = false;
        this.is_failed_message = false;
    },

    /** Send again the failed emails of the message */
    async retryMailTrackingFailedMails() {
        const {notification, orm} = this.store.env.services;
        const count = await orm.call("mail.message", "action_retry_failed_mails", [
            [this.id],
        ]);
        this.can_retry_failed_mails = false;
        if (!count) {
            notification.add(_t("There are no failed emails left to send again."), {
                type: "warning",
            });
            return;
        }
        this.mail_tracking_needs_action = false;
        this.is_failed_message = false;
        notification.add(_t("The failed emails will be sent again shortly."), {
            type: "success",
        });
    },
});
