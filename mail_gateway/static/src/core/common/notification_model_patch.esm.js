import {Notification} from "@mail/core/common/notification_model";
import {fields} from "@mail/model/export";
import {getGatewayIcon} from "../../models/mail_gateway_model.esm";
import {patch} from "@web/core/utils/patch";

patch(Notification.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {string|false|undefined} */
        this.gateway_type = undefined;
        /** @type {string|undefined} */
        this.failure_reason = undefined;
        /** @type {string|false|undefined} */
        this.gateway_failure_summary = false;
        this.gateway_channel_id = fields.One("discuss.channel");
    },
    get isGateway() {
        return this.notification_type === "gateway";
    },
    get icon() {
        if (this.isGateway && !this.isFailure) {
            return getGatewayIcon(this.gateway_type);
        }
        return super.icon;
    },
    get failureMessage() {
        if (this.isGateway && this.gateway_failure_summary) {
            return this.gateway_failure_summary;
        }
        return super.failureMessage;
    },
    get gatewayChannelName() {
        return this.gateway_channel_id?.name || this.gateway_channel_id?.displayName;
    },
});
