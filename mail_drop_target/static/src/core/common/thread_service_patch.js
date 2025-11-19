/** @odoo-module */

import {ThreadService} from "@mail/core/common/thread_service";
import {patch} from "@web/core/utils/patch";
import {sortBy} from "@web/core/utils/arrays";
const FETCH_LIMIT = 30;

patch(ThreadService.prototype, {
    /**
     * @param {import("models").Thread} thread
     * @param {{after: Number, before: Number}}
     */
    async fetchMessages(thread, {after, before} = {}) {
        thread.status = "loading";
        if (thread.type === "chatter" && !thread.id) {
            thread.isLoaded = true;
            return [];
        }
        try {
            // ordered messages received: newest to oldest
            const {messages: rawMessages} = await this.rpc(this.getFetchRoute(thread), {
                ...this.getFetchParams(thread),
                limit: FETCH_LIMIT,
                after,
                before,
            });
            const messages = this.store.Message.insert(
                sortBy(rawMessages, "date").reverse().reverse(),
                {html: true}
            );
            thread.isLoaded = true;
            return messages;
        } catch (e) {
            thread.hasLoadingFailed = true;
            throw e;
        } finally {
            thread.status = "ready";
        }
    },
});
