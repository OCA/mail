import {Notification} from "@mail/core/common/notification_model";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

const WHATSAPP_STATUS_ICONS = {
    sent: "fa fa-whatsapp text-muted",
    delivered: "fa fa-whatsapp text-success",
    read: "fa fa-whatsapp text-info",
};

patch(Notification.prototype, {
    get isWhatsappSent() {
        return this.gateway_type === "whatsapp" && this.notification_status === "sent";
    },
    get statusIcon() {
        if (this.isWhatsappSent && this.whatsapp_status) {
            return WHATSAPP_STATUS_ICONS[this.whatsapp_status];
        }
        return super.statusIcon;
    },
    get statusTitle() {
        if (!this.isWhatsappSent) {
            return super.statusTitle;
        }
        switch (this.whatsapp_status) {
            case "delivered":
                return _t("Delivered");
            case "read":
                return _t("Read");
        }
        return _t("Sent");
    },
});
