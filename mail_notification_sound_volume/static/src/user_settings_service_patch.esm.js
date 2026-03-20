/** @odoo-module */

import {UserSettings} from "@mail/core/common/user_settings_service";
import {patch} from "@web/core/utils/patch";

patch(UserSettings.prototype, {
    notificationVolume: 1.0,

    updateFromCommands(settings) {
        super.updateFromCommands(settings);
        if ("notification_volume" in settings) {
            this.notificationVolume = settings.notification_volume;
        }
    },

    setNotificationVolume(value) {
        this.notificationVolume = parseFloat(value);
        this._saveSettings();
    },

    async _onSaveGlobalSettingsTimeout() {
        this.globalSettingsTimeout = undefined;
        await this.orm.call(
            "res.users.settings",
            "set_res_users_settings",
            [[this.id]],
            {
                new_settings: {
                    push_to_talk_key: this.pushToTalkKey,
                    use_push_to_talk: this.usePushToTalk,
                    voice_active_duration: this.voiceActiveDuration,
                    notification_volume: this.notificationVolume,
                },
            }
        );
    },
});
