import {MailCoreCommon} from "@mail/core/common/mail_core_common_service";
import {patch} from "@web/core/utils/patch";

patch(MailCoreCommon.prototype, {
    setup() {
        super.setup();
        this.busService.subscribe(
            "mail.tracking/set_need_action_done",
            (payload, metadata) => {
                const {id: notifId} = metadata;
                for (const messageId of payload.message_ids) {
                    const message = this.store["mail.message"].get(messageId);
                    if (!message) continue;
                    const failedBox = this.store.failed;
                    if (notifId > failedBox.counter_bus_id) {
                        failedBox.counter--;
                    }
                    failedBox.messages.delete(message);
                    message.delete();
                }
            }
        );
    },
});
