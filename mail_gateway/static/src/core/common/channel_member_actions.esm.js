import {_t} from "@web/core/l10n/translation";
import {registerChannelMemberAction} from "@mail/discuss/core/common/channel_member_actions";

registerChannelMemberAction("gateway-manage-guest", {
    condition: ({member, store}) =>
        store.has_gateway_access &&
        member.channel_id?.channel_type === "gateway" &&
        Boolean(member.guest_id),
    icon: "person_add",
    name: _t("Manage guest"),
    onSelected: ({member, store}) =>
        store.env.services.action.doAction(
            {
                name: _t("Manage guest"),
                type: "ir.actions.act_window",
                res_model: "mail.guest.manage",
                context: {default_guest_id: member.guest_id.id},
                views: [[false, "form"]],
                target: "new",
            },
            {onClose: () => store.fetchChannel(member.channel_id.id)}
        ),
    sequence: 10,
});
