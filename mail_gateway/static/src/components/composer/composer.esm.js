import {t, useProps} from "@odoo/owl";
import {Composer} from "@mail/core/common/composer";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        this.gatewayComposerProps = useProps({
            isGateway: t.boolean().optional(false),
        });
    },
    /** Whether the composer posts a new message through gateway channels. */
    get isGatewayComposer() {
        return this.gatewayComposerProps.isGateway && !this.props.composer.message;
    },
    get SEND_TEXT() {
        if (this.isGatewayComposer) {
            return _t("Send gateway");
        }
        return super.SEND_TEXT;
    },
    get placeholder() {
        if (
            this.isGatewayComposer &&
            !this.props.placeholder &&
            !this.thread?.channel
        ) {
            return _t("Send a message to a gateway...");
        }
        return super.placeholder;
    },
    get isSendButtonDisabled() {
        return (
            super.isSendButtonDisabled ||
            (this.isGatewayComposer && !this.thread?.gateway_notifications?.length)
        );
    },
    async sendMessage() {
        if (!this.isGatewayComposer) {
            return super.sendMessage(...arguments);
        }
        // Core checks the email of the suggested recipients, but gateway messages
        // are only sent to the selected gateway channels.
        this.composerActions.activeAction?.actionPanelClose?.();
        await this.processMessage(async (value) => {
            await this._sendMessage(value, this.postData, this.extraData);
        });
    },
    get postData() {
        const postData = super.postData;
        if (this.isGatewayComposer) {
            postData.isGateway = true;
        }
        return postData;
    },
    async onClickFullComposerGetAction() {
        if (!this.isGatewayComposer) {
            return super.onClickFullComposerGetAction(...arguments);
        }
        this.props.composer.restoredFromFullComposer = false;
        const thread = this.thread;
        const gatewayFollowers = thread.gateway_followers;
        const selectedChannelIds = (thread.gateway_notifications || []).map(
            (notification) => notification.gateway_channel_id
        );
        // Without selection in the chatter, propose every gateway channel of the
        // gateway followers, as it was done before.
        const channelIds = selectedChannelIds.length
            ? selectedChannelIds
            : gatewayFollowers.flatMap((partner) =>
                  partner.gateway_channel_ids.map((channel) => channel.id)
              );
        const context = {
            default_attachment_ids: this.props.composer.attachments.map(
                (attachment) => attachment.id
            ),
            default_body: this.formatDefaultBodyForFullComposer(
                this.props.composer.composerHtml
            ),
            default_model: thread.model,
            default_res_ids: [thread.id],
            default_subtype_xmlid: "mail.mt_comment",
            default_wizard_partner_ids: [
                ...new Set(gatewayFollowers.map((partner) => partner.id)),
            ],
            default_wizard_channel_ids: [...new Set(channelIds)],
            is_full_composer: true,
        };
        const action = {
            name: _t("Gateway message"),
            type: "ir.actions.act_window",
            res_model: "mail.compose.gateway.message",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context,
        };
        const options = {
            onClose: (args) => {
                // Args?.dismiss: click on 'X' or escape, args?.special: 'discard'
                const isDiscard = Boolean(args?.dismiss || args?.special);
                if (!isDiscard) {
                    this.clear();
                    thread.gateway_notifications = [];
                }
                this.props.composer.replyToMessage = undefined;
                this.onCloseFullComposerCallback(isDiscard);
                this.state.isFullComposerOpen = false;
            },
        };
        return {action, options};
    },
});
