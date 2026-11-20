import "@mail/chatter/web/chatter_patch";
import {Chatter} from "@mail/chatter/web_portal_project/chatter";
import {FailedMessage} from "@mail_recipient_tracking/components/failed_message/failed_message.esm";
import {patch} from "@web/core/utils/patch";

Chatter.components = {
    ...Chatter.components,
    FailedMessage,
};

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        Object.assign(this.state, {showFailedMessages: true});
    },

    get failedMessages() {
        return (this.state.thread?.messages ?? []).filter(
            (message) => message.is_failed_message
        );
    },

    toggleFailedMessages() {
        this.state.showFailedMessages = !this.state.showFailedMessages;
    },
});
