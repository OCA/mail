import {Message} from "@mail/core/common/message";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(Message.prototype, {
    onClickLinkGatewayToThread() {
        return this.env.services.action.doAction({
            name: _t("Link Message to thread"),
            type: "ir.actions.act_window",
            res_model: "mail.message.gateway.link",
            context: {default_message_id: this.message.id},
            views: [[false, "form"]],
            target: "new",
        });
    },
    onClickSendWithGateway() {
        return this.env.services.action.doAction({
            name: _t("Send with gateway"),
            type: "ir.actions.act_window",
            res_model: "mail.message.gateway.send",
            context: {
                ...this.message.gateway_channel_data,
                default_message_id: this.message.id,
            },
            views: [[false, "form"]],
            target: "new",
        });
    },
    openGatewayThreadRecord(ev) {
        ev?.preventDefault();
        return this.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_id: this.message.gateway_thread_data.id,
            res_model: this.message.gateway_thread_data.model,
            views: [[false, "form"]],
        });
    },
});
