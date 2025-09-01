import {messageActionsRegistry} from "@mail/core/common/message_actions";

messageActionsRegistry.add("reply", {
    icon: "fa fa-reply",
    title: "Reply",
    onClick: (component) => component.message.messageReply(component.props.message),
    condition: (component) => component.canReply,
});
messageActionsRegistry.add("reply_all", {
    icon: "fa fa-reply-all",
    title: "Reply All",
    onClick: (component) =>
        component.message.messageReply(component.props.message, true),
    condition: (component) => component.canReply,
});
