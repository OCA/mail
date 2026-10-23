import {Thread} from "@mail/core/common/thread_model";
import {fields} from "@mail/model/export";
import {patch} from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        /** Followers of the thread that can be reached through a gateway. */
        this.gateway_followers = fields.Many("res.partner");
        /**
         * Gateway channels selected in the chatter to send the next message to.
         *
         * @type {{partner_id: number, channel_type: "gateway", gateway_channel_id: number}[]}
         */
        this.gateway_notifications = [];
    },
});
