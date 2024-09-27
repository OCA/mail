import {patch} from "@web/core/utils/patch";
import {MailCoreCommon} from "@mail/core/common/mail_core_common_service";

patch(MailCoreCommon.prototype, {
    setup() {
        super.setup();
        this.busService.subscribe(
            "mail.tracking/set_need_action_done",
            (payload, metadata) => {
                const {id: notifId} = metadata;
                const {message_ids: messageIds} = payload;
                for (const id of messageIds) {
                    const message = this.store.Message.get({id});
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
