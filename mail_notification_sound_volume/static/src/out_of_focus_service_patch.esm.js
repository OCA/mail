/** @odoo-module */

import {OutOfFocusService} from "@mail/core/common/out_of_focus_service";
import {patch} from "@web/core/utils/patch";
import {url} from "@web/core/utils/urls";

patch(OutOfFocusService.prototype, {
    async _playSound() {
        if (this.canPlayAudio && this.multiTab.isOnMainTab()) {
            if (!this.audio) {
                this.audio = new Audio();
                this.audio.src = this.audio.canPlayType("audio/ogg; codecs=vorbis")
                    ? url("/mail/static/src/audio/ting.ogg")
                    : url("/mail/static/src/audio/ting.mp3");
            }
            const userSettings = this.env.services["mail.user_settings"];
            this.audio.volume =
                userSettings && userSettings.notificationVolume !== undefined
                    ? userSettings.notificationVolume
                    : 0.7;
            try {
                await this.audio.play();
            } catch {
                // Ignore errors due to the user not having interacted
                // with the page before playing the sound.
            }
        }
    },
});
