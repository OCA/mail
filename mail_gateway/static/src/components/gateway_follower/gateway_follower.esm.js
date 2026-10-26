import {Component, types, useProps} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

/**
 * Selector of the gateway channel used to reach a follower from the chatter.
 * The selection is stored in `thread.gateway_notifications`, which is sent
 * along with the message.
 */
export class GatewayFollower extends Component {
    static template = "mail_gateway.GatewayFollower";

    setup() {
        this.store = useService("mail.store");
        this.props = useProps({
            follower: types.instanceOf(this.store["res.partner"]),
            thread: types.instanceOf(this.store["mail.thread"]),
        });
        this.clearSelection();
    }

    get followerChannelIds() {
        return this.props.follower.gateway_channel_ids.map((channel) => channel.id);
    }

    get selectedChannelId() {
        return this.props.thread.gateway_notifications.find((notification) =>
            this.followerChannelIds.includes(notification.gateway_channel_id)
        )?.gateway_channel_id;
    }

    clearSelection() {
        const followerChannelIds = this.followerChannelIds;
        this.props.thread.gateway_notifications =
            this.props.thread.gateway_notifications.filter(
                (notification) =>
                    !followerChannelIds.includes(notification.gateway_channel_id)
            );
    }

    /** @param {Event} ev */
    onChangeGatewayChannel(ev) {
        const channelId = parseInt(ev.target.value, 10);
        this.clearSelection();
        if (channelId) {
            this.props.thread.gateway_notifications = [
                ...this.props.thread.gateway_notifications,
                {
                    partner_id: this.props.follower.id,
                    channel_type: "gateway",
                    gateway_channel_id: channelId,
                },
            ];
        }
    }
}
