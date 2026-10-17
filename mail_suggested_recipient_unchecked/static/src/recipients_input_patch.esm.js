/* Copyright 2026 ACSONE SA/NV
 * License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl). */

import {RecipientsInput} from "@mail/core/web/recipients_input";
import {patch} from "@web/core/utils/patch";

patch(RecipientsInput.prototype, {
    /** @returns {SuggestedRecipient[]} suggestions not selected yet */
    getUncheckedSuggestedRecipients() {
        return this.props.thread.uncheckedSuggestedRecipients.filter(
            (suggestion) =>
                !this.getAllMailThreadRecipients().some((recipient) =>
                    suggestion.partner_id
                        ? recipient.partner_id === suggestion.partner_id
                        : recipient.email === suggestion.email
                )
        );
    },

    /** @param {SuggestedRecipient} recipient */
    onClickUncheckedSuggestedRecipient(recipient) {
        this.insertAdditionalRecipient({...recipient});
    },
});
