import {MailGuest} from "@mail/core/common/mail_guest_model";
import {fields} from "@mail/model/export";
import {patch} from "@web/core/utils/patch";

patch(MailGuest.prototype, {
    setup() {
        super.setup(...arguments);
        this.gateway_id = fields.One("mail.gateway");
    },
});
