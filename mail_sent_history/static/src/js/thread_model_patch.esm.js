import {Thread} from "@mail/core/common/thread_model";
import {patch} from "@web/core/utils/patch";

patch(Thread.prototype, {
    getFetchRoute() {
        if (this.model === "mail.box" && this.id === "sent_history") {
            return "/mail/sent_history/messages";
        }
        return super.getFetchRoute(...arguments);
    },
    async post() {
        const message = await super.post(...arguments);
        if (message?.isSelfAuthored) {
            const sentHistory = this.store.sent_history;
            if (sentHistory && !sentHistory.messages.includes(message)) {
                sentHistory.messages.add(message);
            }
        }
        return message;
    },
});
