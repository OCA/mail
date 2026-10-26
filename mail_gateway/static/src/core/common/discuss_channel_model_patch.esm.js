import {DiscussChannel} from "@mail/discuss/core/common/discuss_channel_model";
import {fields} from "@mail/model/export";
import {patch} from "@web/core/utils/patch";

patch(DiscussChannel.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {string|undefined} */
        this.anonymous_name = undefined;
        this.gateway_id = fields.One("mail.gateway");
        /** Contact linked to the gateway channel (if any). */
        this.gateway_partner_id = fields.One("res.partner");
    },
    get isGateway() {
        return this.channel_type === "gateway";
    },
    /** Kept for compatibility with the former `thread.gateway` field. */
    get gateway() {
        return this.gateway_id;
    },
    get allowedToLeaveChannelTypes() {
        return [...super.allowedToLeaveChannelTypes, "gateway"];
    },
    get chatChannelTypes() {
        return [...super.chatChannelTypes, "gateway"];
    },
    get memberListTypes() {
        return [...super.memberListTypes, "gateway"];
    },
    /** Guest writing through the gateway, when there is only one. */
    get gatewayGuest() {
        if (!this.isGateway) {
            return undefined;
        }
        const guests = this.channel_member_ids
            .map((member) => member.guest_id)
            .filter((guest) => guest);
        return guests.length === 1 ? guests[0] : undefined;
    },
    /** Contact to open from the gateway channel. */
    get gatewayContact() {
        if (!this.isGateway) {
            return undefined;
        }
        return this.gateway_partner_id || this.correspondent?.partner_id;
    },
});
