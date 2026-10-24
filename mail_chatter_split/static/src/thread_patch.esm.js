import {Thread} from "@mail/core/common/thread";
import {patch} from "@web/core/utils/patch";

patch(Thread.prototype, {
    /**
     * Restrict the rendered messages to the ones matching the chatter view mode
     * selected on the thread, keeping the ordering computed by the core getter.
     * @returns {Array}
     */
    get orderedMessages() {
        const messages = super.orderedMessages;
        const thread = this.props.thread;
        if (!thread || !thread.chatterViewMode || thread.chatterViewMode === "all") {
            return messages;
        }
        const displayed = new Set(thread.displayedMessages);
        return messages.filter((msg) => displayed.has(msg));
    },
});
