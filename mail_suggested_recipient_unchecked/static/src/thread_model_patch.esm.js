/* Copyright 2026 ACSONE SA/NV
 * License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl). */

import {Thread} from "@mail/core/common/thread_model";
import {fields} from "@mail/core/common/record";
import {patch} from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        /* Suggested recipients that are proposed to the user but not selected:
         * they only receive the message once added to the additional recipients. */
        this.uncheckedSuggestedRecipients = fields.Attr([]);
        // Every recipient of suggestedRecipients is notified, so move them away
        this.suggestedRecipients = fields.Attr([], {
            onUpdate() {
                if (this.suggestedRecipients.length) {
                    this.uncheckedSuggestedRecipients = this.suggestedRecipients;
                    this.suggestedRecipients = [];
                }
            },
        });
    },
});
