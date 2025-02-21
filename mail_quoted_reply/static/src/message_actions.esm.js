import {messageActionsRegistry} from "@mail/core/common/message_actions";

messageActionsRegistry.add("reply", {
    icon: "fa fa-reply",
    title: "Reply",
    onClick: (component) => component.message.messageReply(component.props.message),
    condition: (component) => component.canReply,
});
