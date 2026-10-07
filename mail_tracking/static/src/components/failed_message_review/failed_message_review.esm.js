import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";

const {Component, useState} = owl;

export class FailedMessageReview extends Component {
    static props = ["message"];
    static template = "mail_tracking.FailedMessageReview";

    setup() {
        this.message = useState(this.props.message);
        this.orm = useService("orm");
        this.notification = useService("notification");
    }
    async setFailedMessageReviewed() {
        await this.orm.call("mail.message", "set_need_action_done", [
            [this.message.id],
        ]);
    }
    async retryFailedMessage() {
        const sent = await this.orm.call("mail.message", "retry_failed_message", [
            [this.message.id],
        ]);
        this.notification.add(
            sent
                ? _t("The email has been sent again.")
                : _t("The email could not be sent again."),
            {type: sent ? "success" : "danger"}
        );
    }
    get thread() {
        return this.props.message.thread;
    }
    get failed_recipients() {
        const error_states = ["error", "rejected", "spam", "bounced", "soft-bounced"];
        return this.message.partner_trackings.filter((message) => {
            return error_states.includes(message.status);
        });
    }
}
