import {Message} from "@mail/core/common/message_model";
import {patch} from "@web/core/utils/patch";

patch(Message.prototype, {
    async messageReply(message, reply_all = false) {
        var self = this;
        const thread = message.thread;
        await this.store.env.services.orm
            .call("mail.message", "reply_message", [message.id, reply_all])
            .then(function (result) {
                return self.store.env.services.action.doAction(result, {
                    onClose: async () => {
                        await self.store.env.services["mail.store"].Thread.getOrFetch(
                            thread,
                            ["messages"]
                        );
                        self.store.env.bus.trigger("update-messages");
                    },
                });
            });
    },
});
