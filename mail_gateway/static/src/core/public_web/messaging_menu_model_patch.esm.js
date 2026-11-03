import {
    MENU_TABS,
    MessagingMenu,
} from "@mail/core/public_web/messaging_menu/messaging_menu_model";
import {_t} from "@web/core/l10n/translation";
import {fields} from "@mail/model/export";
import {getGatewayIcon} from "../../models/mail_gateway_model.esm";
import {patch} from "@web/core/utils/patch";

MENU_TABS.GATEWAY = "gateway";

/**
 * "Gateway" tab of the messaging menu and Discuss sidebar: it lists the gateway
 * channels of the user, with a filter for each gateway the user is member of.
 * Server side domains: `controllers/messaging_menu.py`.
 */
patch(MessagingMenu.prototype, {
    setup() {
        super.setup(...arguments);
        this.gatewayTab = fields.One("MessagingMenuTab", {
            compute() {
                if (!this.store.has_gateway_access) {
                    return;
                }
                const gateways = [...this.store.gateways].sort(
                    (g1, g2) => g1.id - g2.id
                );
                return {
                    id: MENU_TABS.GATEWAY,
                    icon: getGatewayIcon(
                        gateways.length === 1 && gateways[0].gateway_type
                    ),
                    activeIcon: getGatewayIcon(
                        gateways.length === 1 && gateways[0].gateway_type
                    ),
                    label: _t("Gateway"),
                    sequence: 95,
                    emptyState: {
                        title: _t("No gateway conversation yet!"),
                        subtitle: _t(
                            "Conversations received through your gateways will appear here."
                        ),
                    },
                    filters: [
                        {
                            id: "gateway_unread",
                            text: _t("Unread"),
                            includesChannel: (c) => c.isUnread,
                        },
                        ...(gateways.length > 1
                            ? gateways.map((gateway) => ({
                                  id: `gateway_${gateway.id}`,
                                  text: gateway.name,
                                  includesChannel: (c) => c.gateway_id?.eq(gateway),
                              }))
                            : []),
                    ],
                    includesChannel: (c) =>
                        c.channel_type === "gateway" &&
                        (c.self_member_id?.is_pinned || c.isLocallyPinned),
                    recordType: "discuss.channel",
                };
            },
            eager: true,
        });
    },
});
