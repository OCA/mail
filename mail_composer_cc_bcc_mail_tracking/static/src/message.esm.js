import {Message} from "@mail/core/common/message";
import {patch} from "@web/core/utils/patch";
import {useState} from "@odoo/owl";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        // Default view (single "To" vs full To/Cc/Bcc) comes from the company
        // setting exposed on the message.
        this.ccBccState = useState({expanded: this.message.recipientsDefaultExpanded});
    },
    get recipientsToggleAllowed() {
        return this.message.recipientsAllowToggle;
    },
    get toTrackings() {
        return (this.message.partner_trackings || []).filter((t) => t.isTo);
    },
    get ccTrackings() {
        return (this.message.partner_trackings || []).filter((t) => t.isCc);
    },
    get bccTrackings() {
        return (this.message.partner_trackings || []).filter((t) => t.isBcc);
    },
    toggleCcBcc() {
        if (!this.recipientsToggleAllowed) {
            return;
        }
        this.ccBccState.expanded = !this.ccBccState.expanded;
    },
});
