import {_t} from "@web/core/l10n/translation";
import {registerThreadAction} from "@mail/core/common/thread_actions";

registerThreadAction("open-gw-new-partner", {
    condition: ({channel, owner, store}) =>
        store.has_gateway_access &&
        Boolean(channel?.gatewayGuest) &&
        !owner.isDiscussSidebarChannelActions,
    icon: "person_add",
    name: _t("New Partner"),
    onSelected: ({channel, store}) =>
        store.env.services.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "mail.guest.manage",
                context: {default_guest_id: channel.gatewayGuest.id},
                views: [[false, "form"]],
                target: "new",
            },
            {onClose: () => store.fetchChannel(channel.id)}
        ),
    sequence: 18,
    sequenceGroup: 7,
});
registerThreadAction("open-gw-profile", {
    condition: ({channel, owner, store}) =>
        store.has_gateway_access &&
        Boolean(channel?.gatewayContact) &&
        !owner.isDiscussSidebarChannelActions,
    icon: "account_circle",
    name: _t("Open Contact"),
    onSelected: ({channel, store}) =>
        store.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: channel.gatewayContact.id,
            views: [[false, "form"]],
        }),
    sequence: 17,
    sequenceGroup: 7,
});
