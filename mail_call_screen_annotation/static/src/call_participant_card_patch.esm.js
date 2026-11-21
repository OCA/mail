/* Copyright 2026 Fasil
 * License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl). */

import {CallParticipantCard} from "@mail/discuss/call/common/call_participant_card";
import {ScreenAnnotationOverlay} from "@mail_call_screen_annotation/screen_annotation_overlay.esm";
import {patch} from "@web/core/utils/patch";

CallParticipantCard.components = {
    ...CallParticipantCard.components,
    ScreenAnnotationOverlay,
};

patch(CallParticipantCard.prototype, {
    /**
     * Whether this card is the user's own shared screen, hidden by Odoo against
     * the infinite mirror effect.
     *
     * Recent 20.0 builds keep that state in `rtc.isScreenTrackPaused`, older
     * ones only on the track itself: both are supported.
     */
    get isOwnScreenPaused() {
        const rtc = this.rtc;
        if (!rtc.screenTrack || !this.rtcSession?.eq(rtc.selfSession)) {
            return false;
        }
        return rtc.isScreenTrackPaused ?? !rtc.screenTrack.enabled;
    },

    /** Only the large view of a shared screen can be drawn on. */
    get showsScreenAnnotation() {
        return Boolean(
            this.props.cardData.type === "screen" &&
            this.rtcSession &&
            this.hasVideo &&
            this.isActiveCall &&
            !this.props.minimized &&
            !this.props.inset &&
            !this.props.isSidebarItem &&
            !this.isOwnScreenPaused
        );
    },
});
