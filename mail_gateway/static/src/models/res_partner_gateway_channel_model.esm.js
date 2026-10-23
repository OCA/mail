import {Record, fields} from "@mail/model/export";

export class ResPartnerGatewayChannel extends Record {
    static _name = "res.partner.gateway.channel";

    /** @type {Number} */
    id;
    /** @type {String} */
    name;
    gateway_id = fields.One("mail.gateway");
}
ResPartnerGatewayChannel.register();
