import {Component, t} from "@odoo/owl";
import {propComputed} from "@mail/utils/common/hooks";
import {useService} from "@web/core/utils/hooks";

export class FailedMessageReview extends Component {
    static template = "mail_recipient_tracking.FailedMessageReview";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.message = propComputed(
            "message",
            t.instanceOf(this.store["mail.message"])
        );
    }

    async onClickSetReviewed() {
        await this.message().setMailTrackingReviewed();
    }

    async onClickRetry() {
        await this.message().retryMailTrackingFailedMails();
    }
}
