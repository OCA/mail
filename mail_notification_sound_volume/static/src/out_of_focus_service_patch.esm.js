import {OutOfFocusService} from "@mail/core/common/out_of_focus_service";
import {patch} from "@web/core/utils/patch";

patch(OutOfFocusService.prototype, {
    async _playSound() {
        if (
            this.canPlayAudio &&
            this.store.settings.messageSound &&
            (await this.multiTab.isOnMainTab())
        ) {
            const volume = this.store.settings.notification_volume ?? 1;
            this.soundEffectService.play("new-message", {volume});
        }
    },
});
