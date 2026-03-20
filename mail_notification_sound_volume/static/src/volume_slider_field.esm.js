/** @odoo-module */

import {Component} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import {standardFieldProps} from "@web/views/fields/standard_field_props";
import {url} from "@web/core/utils/urls";

export class VolumeSliderField extends Component {
    static template = "mail_notification_sound_volume.VolumeSliderField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.testAudio = null;
    }

    get value() {
        return this.props.record.data[this.props.name] || 0;
    }

    get percentage() {
        return Math.round(this.value * 100);
    }

    onChange(ev) {
        const value = parseFloat(ev.target.value);
        this.props.record.update({[this.props.name]: value});
        const userSettings = this.env.services["mail.user_settings"];
        if (userSettings) {
            userSettings.notificationVolume = value;
        }
    }

    onTestSound() {
        if (!this.testAudio) {
            this.testAudio = new Audio();
            this.testAudio.src = this.testAudio.canPlayType("audio/ogg; codecs=vorbis")
                ? url("/mail/static/src/audio/ting.ogg")
                : url("/mail/static/src/audio/ting.mp3");
        }
        this.testAudio.volume = this.value;
        this.testAudio.currentTime = 0;
        this.testAudio.play().catch(() => {
            // Ignore autoplay errors
        });
    }
}

export const volumeSliderField = {
    component: VolumeSliderField,
    displayName: _t("Volume Slider"),
    supportedTypes: ["float"],
};

registry.category("fields").add("volume_slider", volumeSliderField);
