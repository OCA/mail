import {Store} from "@mail/core/common/store_service";
import {fields} from "@mail/model/export";
import {patch} from "@web/core/utils/patch";

/** Recipient keys added by the core from the suggested/additional recipients. */
const EMAIL_RECIPIENT_KEYS = [
    "partner_cc_emails",
    "partner_cc_ids",
    "partner_emails",
    "partner_ids",
];

patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
        /** Whether the current user belongs to the gateway users group. */
        this.has_gateway_access = false;
        /** Gateways the current user is a member of. */
        this.gateways = fields.Many("mail.gateway");
    },
    async getMessagePostParams({postData, thread}) {
        const params = await super.getMessagePostParams(...arguments);
        if (postData.isGateway) {
            // A gateway message is only sent to the selected gateway channels: drop
            // the email recipients added by the core (they are not shown in the
            // gateway composer), but keep the mentions.
            for (const key of EMAIL_RECIPIENT_KEYS) {
                delete params.post_data[key];
            }
            const mentionedPartnerIds = (postData.mentionedPartners || []).map(
                (partner) => partner.id
            );
            if (mentionedPartnerIds.length) {
                params.post_data.partner_ids = mentionedPartnerIds;
            }
            if (thread.gateway_notifications?.length) {
                params.post_data.gateway_notifications = thread.gateway_notifications;
            }
        }
        return params;
    },
});
