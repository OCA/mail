import {Record} from "@mail/core/common/record";
import {Store} from "@mail/core/common/store_service";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
        this.failed = Record.one("Thread");
    },

    onStarted() {
        super.onStarted(...arguments);
        this.failed = {
            id: "failed",
            model: "mail.box",
            name: _t("Failed"),
        };
    },
});
