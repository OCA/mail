import {registerMessageAction} from "@mail/core/common/message_actions";

registerMessageAction("mail_print", {
    condition: ({message}) => !message.isNote,
    icon: "fa fa-print",
    name: "Print Message",
    onSelected: ({message, owner}) => {
        owner.env.services.action.doAction("mail_print.mail_message_report", {
            additionalContext: {
                active_id: message.id,
                active_ids: [message.id],
                active_model: "mail.message",
            },
        });
    },
    sequence: 10,
});
