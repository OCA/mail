import {Thread} from "@mail/core/common/thread_model";
import {fields} from "@mail/core/common/record";

import {patch} from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.chatterViewMode = fields.Attr("all");
    },

    get displayedMessages() {
        const messages = this.nonEmptyMessages;
        if (!this.chatterViewMode || this.chatterViewMode === "all") {
            return messages;
        }
        if (this.chatterViewMode === "messages") {
            return messages.filter((msg) => this._isUserMessage(msg));
        }
        if (this.chatterViewMode === "logs") {
            return messages.filter((msg) => this._isLogMessage(msg));
        }
        if (this.chatterViewMode === "activities") {
            return messages.filter((msg) => this._isActivity(msg));
        }
        return messages;
    },

    /**
     * Check if a message is a user-generated message
     * @param {Object} msg
     * @returns {Boolean}
     */
    _isUserMessage(msg) {
        const userTypes = ["comment", "email", "email_outgoing"];
        if (userTypes.includes(msg.message_type)) {
            return true;
        }
        if (
            ["auto_comment", "user_notification"].includes(msg.message_type) &&
            !msg.isBodyEmpty
        ) {
            return true;
        }
        return false;
    },

    /**
     * Check if a message is a system-generated log
     * @param {Object} msg
     * @returns {Boolean}
     */
    _isLogMessage(msg) {
        if (msg.message_type === "notification") {
            return true;
        }
        if (msg.trackingValues && msg.trackingValues.length > 0) {
            return true;
        }
        if (msg.isBodyEmpty && msg.subtype_id?.description) {
            return true;
        }
        return false;
    },

    /**
     * Check if a message is an activity
     * @param {Object} msg
     * @returns {Boolean}
     */
    _isActivity(msg) {
        return (
            msg.message_type === "user_notification" ||
            (msg.subtype_id?.description &&
                msg.subtype_id.description.includes("Activity"))
        );
    },
});
