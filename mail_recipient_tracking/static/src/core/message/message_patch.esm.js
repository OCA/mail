import {FailedMessageReview} from "@mail_recipient_tracking/components/failed_message_review/failed_message_review.esm";
import {Message} from "@mail/core/common/message";
import {MessageTracking} from "@mail_recipient_tracking/components/message_tracking/message_tracking.esm";
import {getFailedRecipients} from "@mail_recipient_tracking/core/message/message_model_patch.esm";
import {patch} from "@web/core/utils/patch";

Message.components = {
    ...Message.components,
    FailedMessageReview,
    MessageTracking,
};

patch(Message.prototype, {
    get failedRecipients() {
        return getFailedRecipients(this.message);
    },
});
