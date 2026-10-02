/*  Copyright 2026 ACSONE SA/NV
    License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
*/
import {registry} from "@web/core/registry";

registry
    .category("web_tour.tours")
    .add("mail_suggested_recipient_unchecked.mail_suggested_recipient_unchecked_tour", {
        steps: () => [
            {
                content: "Open the message composer",
                trigger: "button.o-mail-Chatter-sendMessage",
                run: "click",
            },
            {
                content: "The suggested recipient is proposed",
                trigger:
                    ".o-mail-RecipientsInput-uncheckedSuggestion:contains('Suggested Recipient')",
            },
            {
                content: "The suggested recipient is not selected",
                trigger:
                    ".o-mail-RecipientsInput:not(:has(.o_tag_badge_text:contains('Suggested Recipient')))",
            },
            {
                content: "Select the suggested recipient",
                trigger:
                    ".o-mail-RecipientsInput-uncheckedSuggestion:contains('Suggested Recipient')",
                run: "click",
            },
            {
                content: "The suggested recipient is selected",
                trigger:
                    ".o-mail-RecipientsInput .o_tag_badge_text:contains('Suggested Recipient')",
            },
            {
                content: "The suggestion is no longer proposed",
                trigger:
                    ".o-mail-RecipientsInput:not(:has(.o-mail-RecipientsInput-uncheckedSuggestion))",
            },
        ],
    });
