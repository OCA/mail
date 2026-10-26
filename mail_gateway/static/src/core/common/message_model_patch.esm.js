import {Message} from "@mail/core/common/message_model";
import {patch} from "@web/core/utils/patch";
import {router} from "@web/core/browser/router";
import {url} from "@web/core/utils/urls";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {string|false|undefined} */
        this.gateway_type = undefined;
        /**
         * Gateway channels (and their partners) where the message could still be
         * sent to with the "Send with gateway" action.
         *
         * @type {{channels: number[], partners: number[]}|undefined}
         */
        this.gateway_channel_data = undefined;
        /**
         * Record the gateway message has been linked to.
         *
         * @type {{id: number, model: string, name: string}|{}|undefined}
         */
        this.gateway_thread_data = undefined;
    },
    get hasGatewayThread() {
        return Boolean(this.gateway_thread_data?.model);
    },
    get resUrl() {
        if (!this.hasGatewayThread) {
            return super.resUrl;
        }
        return url(
            router.stateToUrl({
                model: this.gateway_thread_data.model,
                resId: this.gateway_thread_data.id,
            })
        );
    },
    get editable() {
        // Messages already sent through a gateway can't be edited.
        return super.editable && !this.gateway_type;
    },
});
