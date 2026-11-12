import {_t} from "@web/core/l10n/translation";
import {registerMessageAction} from "@mail/core/common/message_actions";

registerMessageAction("link_gateway_to_thread", {
    condition: ({message, store, thread}) =>
        store.has_gateway_access &&
        message.gateway_type &&
        thread?.model === "discuss.channel",
    icon: "link",
    name: _t("Link to thread"),
    onSelected: ({message, store}) =>
        store.env.services.action.doAction(
            {
                name: _t("Link Message to thread"),
                type: "ir.actions.act_window",
                res_model: "mail.message.gateway.link",
                context: {default_message_id: message.id},
                views: [[false, "form"]],
                target: "new",
            },
            {
                onClose: (infos) => {
                    // Show the linked message on the record's chatter, if open
                    const linkedThread = infos?.gateway_linked_thread;
                    if (linkedThread) {
                        store["mail.thread"].get(linkedThread)?.fetchNewMessages();
                    }
                },
            }
        ),
    sequence: 20,
});
registerMessageAction("send_with_gateway", {
    condition: ({message, store, thread}) =>
        store.has_gateway_access &&
        !message.gateway_type &&
        thread &&
        thread.model !== "discuss.channel" &&
        message.gateway_channel_data?.channels?.length > 0,
    icon: "forward",
    name: _t("Send with gateway"),
    onSelected: ({message, store}) =>
        store.env.services.action.doAction({
            name: _t("Send with gateway"),
            type: "ir.actions.act_window",
            res_model: "mail.message.gateway.send",
            context: {
                ...message.gateway_channel_data,
                default_message_id: message.id,
            },
            views: [[false, "form"]],
            target: "new",
        }),
    sequence: 20,
});
