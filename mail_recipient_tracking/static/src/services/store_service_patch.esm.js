import {Store} from "@mail/core/common/store_service";
import {_t} from "@web/core/l10n/translation";
import {fields} from "@mail/core/common/record";
import {patch} from "@web/core/utils/patch";

patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
        this.failed = fields.One("Thread");
    },

    onStarted() {
        super.onStarted(...arguments);
        this.failed = {
            id: "failed",
            model: "mail.box",
            display_name: _t("Failed"),
        };
    },
});
