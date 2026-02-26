/* @odoo-module */

import {Messaging} from "@mail/core/common/messaging_service";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(Messaging.prototype, {
    /** @override */
    setup(env, services) {
        super.setup(env, services);
        this.store.discuss.sent_history = this.store.Thread.insert({
            id: "sent_history",
            model: "mail.box",
            name: _t("Sent History"),
            type: "mailbox",
            isLoaded: true,
        });
    },
});
