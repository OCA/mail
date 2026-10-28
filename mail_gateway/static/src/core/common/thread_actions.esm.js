import {_t} from "@web/core/l10n/translation";
import {threadActionsRegistry} from "@mail/core/common/thread_actions";

/*
 * Conditions are evaluated on every render: they must stay synchronous and free
 * of side effects. Starting an RPC and re-rendering the owner from here keeps
 * the Discuss fiber from completing (no messages are shown). The data they need
 * (gateway partner and guest) comes with the channel store data.
 */
function isVisibleChannel(owner, thread) {
    return (
        thread?.model === "discuss.channel" &&
        (!owner.props.chatWindow || owner.props.chatWindow.isOpen)
    );
}

function getProfilePartnerId(thread) {
    if (thread.channel_type === "gateway") {
        return thread.gateway_partner_id || false;
    }
    return thread.correspondent?.partner_id?.id || false;
}

threadActionsRegistry
    .add("open-gw-new-partner", {
        condition: ({owner, thread}) =>
            isVisibleChannel(owner, thread) && Boolean(thread.gateway_guest_id),
        icon: "fa fa-fw fa-address-book",
        name: _t("New Partner"),
        async open({owner, thread}) {
            const guestId = thread.gateway_guest_id;
            if (!guestId) {
                return;
            }
            await owner.env.services.action.doAction(
                {
                    type: "ir.actions.act_window",
                    res_model: "mail.guest.manage",
                    context: {default_guest_id: guestId},
                    views: [[false, "form"]],
                    target: "new",
                },
                {
                    // Refresh the gateway partner/guest once the guest is managed
                    onClose: () =>
                        thread.store.fetchStoreData("discuss.channel", [thread.id]),
                }
            );
        },
        iconLarge: "fa fa-fw fa-lg fa-address-book",
        sequence: 18,
    })
    .add("open-gw-profile", {
        condition: ({owner, thread}) =>
            isVisibleChannel(owner, thread) && Boolean(getProfilePartnerId(thread)),
        icon: "fa fa-fw fa-user-circle-o",
        name: _t("Open Contact"),
        async open({owner, thread}) {
            await owner.env.services.action.doAction({
                type: "ir.actions.act_window",
                res_model: "res.partner",
                res_id: getProfilePartnerId(thread),
                views: [[false, "form"]],
            });
        },
        iconLarge: "fa fa-fw fa-lg fa-user-circle-o",
        sequence: 17,
    });
