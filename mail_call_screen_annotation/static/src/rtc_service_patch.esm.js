/* Copyright 2026 Fasil
 * License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl). */

import {ANNOTATION_MESSAGE_TYPE} from "@mail_call_screen_annotation/screen_annotation_service.esm";
import {Rtc} from "@mail/discuss/call/common/rtc_service";
import {patch} from "@web/core/utils/patch";

patch(Rtc.prototype, {
    async _handleNetworkUpdates({detail: {name, payload}}) {
        if (
            name === "broadcast" &&
            payload?.message?.type === ANNOTATION_MESSAGE_TYPE
        ) {
            if (this.localChannel) {
                this.store.env.services["discuss.screen_annotation"]?.receive(
                    payload.senderId,
                    payload.message
                );
            }
            return;
        }
        return super._handleNetworkUpdates(...arguments);
    },
});
