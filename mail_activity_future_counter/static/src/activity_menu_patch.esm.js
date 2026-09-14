import {Store} from "@mail/core/common/store_service";
import {fields} from "@mail/core/common/record";
import {patch} from "@web/core/utils/patch";

patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
        this.activityFutureCounter = fields.Attr(0);
    },
    onUpdateActivityGroups() {
        super.onUpdateActivityGroups(...arguments);
        let futureTotal = 0;
        for (const group of this.activityGroups) {
            futureTotal += group.planned_count || 0;
        }
        this.activityFutureCounter = futureTotal;
    },
});
