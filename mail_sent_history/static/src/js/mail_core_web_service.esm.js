/** @odoo-module **/

import {MailCoreWeb} from "@mail/core/web/mail_core_web_service";
import {patch} from "@web/core/utils/patch";

patch(MailCoreWeb.prototype, {
    setup() {
        super.setup(...arguments);

        this.messagingService.isReady.then(async () => {
            const res = await this.env.services.orm.call(
                "mail.message",
                "get_sent_history",
                [],
                {}
            );

            const sentHistory = this.store.discuss.sent_history;
            const inserted = this.store.Message.insert(res.messages, {html: true});

            for (const message of inserted) {
                sentHistory.messages.add(message);
            }
        });
    },
});
