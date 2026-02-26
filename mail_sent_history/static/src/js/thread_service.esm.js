/* @odoo-module */

import {ThreadService} from "@mail/core/common/thread_service";
import {patch} from "@web/core/utils/patch";

patch(ThreadService.prototype, {
    async post() {
        const message = await super.post(...arguments);

        if (message?.isSelfAuthored) {
            if (!this.store.discuss.sent_history.messages.includes(message)) {
                this.store.discuss.sent_history.messages.add(message);
            }
        }

        return message;
    },
});
