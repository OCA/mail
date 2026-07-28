import {Message} from "@mail/core/common/message_model";
import {Record} from "@mail/core/common/record";
import {patch} from "@web/core/utils/patch";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.recipientsDefaultExpanded = Record.attr(false);
        this.recipientsAllowToggle = Record.attr(true);
    },
});
