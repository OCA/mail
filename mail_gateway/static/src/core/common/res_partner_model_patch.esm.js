import {ResPartner} from "@mail/core/common/res_partner_model";
import {fields} from "@mail/model/export";
import {patch} from "@web/core/utils/patch";

patch(ResPartner.prototype, {
    setup() {
        super.setup(...arguments);
        this.gateway_channel_ids = fields.Many("res.partner.gateway.channel");
    },
});
