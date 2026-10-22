import {Component, proxy, t} from "@odoo/owl";
import {AvatarCard} from "@mail/core/web/avatar_card/avatar_card";
import {FailedMessageReview} from "@mail_recipient_tracking/components/failed_message_review/failed_message_review.esm";
import {MessageTracking} from "@mail_recipient_tracking/components/message_tracking/message_tracking.esm";
import {RelativeTime} from "@mail/core/common/relative_time";
import {getFailedRecipients} from "@mail_recipient_tracking/core/message/message_model_patch.esm";
import {propComputed} from "@mail/utils/common/hooks";
import {usePopover} from "@web/core/popover/popover_hook";
import {useService} from "@web/core/utils/hooks";

export class FailedMessage extends Component {
    static template = "mail_recipient_tracking.FailedMessage";
    static components = {
        RelativeTime,
        MessageTracking,
        FailedMessageReview,
    };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.message = propComputed(
            "message",
            t.instanceOf(this.store["mail.message"])
        );
        this.avatarCard = usePopover(AvatarCard);
        this.state = proxy({showDetails: false});
    }

    get failedRecipients() {
        return getFailedRecipients(this.message());
    }

    get hasAuthorClickable() {
        return Boolean(this.message().author_id);
    }

    async onClickJump() {
        await this.env.messageHighlight?.highlightMessage(this.message());
    }

    onClickAvatar(ev) {
        if (!this.hasAuthorClickable || this.avatarCard.isOpen) {
            return;
        }
        this.avatarCard.open(ev.currentTarget, {
            id: this.message().author_id.id,
            model: "res.partner",
        });
    }

    toggleDetails() {
        this.state.showDetails = !this.state.showDetails;
    }
}
