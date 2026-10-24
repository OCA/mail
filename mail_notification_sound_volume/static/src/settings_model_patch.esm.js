import {Settings} from "@mail/core/common/settings_model";
import {fields} from "@mail/core/common/record";
import {patch} from "@web/core/utils/patch";

patch(Settings.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification_volume = fields.Attr(1.0);
    },
});
