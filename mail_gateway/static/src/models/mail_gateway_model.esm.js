import {Record} from "@mail/model/export";

/**
 * Icon (from the `oi` icon font) used for each gateway type. Gateway modules can
 * add their own entry, e.g. `GATEWAY_ICONS.whatsapp = "oi_whatsapp"`.
 *
 * @type {Object<string, string>}
 */
export const GATEWAY_ICONS = {};
export const DEFAULT_GATEWAY_ICON = "forum";

/**
 * @param {String} [gatewayType]
 * @returns {String}
 */
export function getGatewayIcon(gatewayType) {
    return GATEWAY_ICONS[gatewayType] || DEFAULT_GATEWAY_ICON;
}

export class MailGateway extends Record {
    static _name = "mail.gateway";

    /** @type {Number} */
    id;
    /** @type {String} */
    name;
    /** @type {String} */
    gateway_type;

    /** Kept for compatibility with the former `{id, name, type}` format. */
    get type() {
        return this.gateway_type;
    }

    get icon() {
        return getGatewayIcon(this.gateway_type);
    }
}
MailGateway.register();
