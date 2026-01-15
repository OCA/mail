/** @odoo-module **/

import {ActivityMenu} from "@mail/core/web/activity_menu";
import {patch} from "@web/core/utils/patch";

patch(ActivityMenu.prototype, {
    async fetchSystrayActivities() {
        await super.fetchSystrayActivities();
        let futureTotal = 0;
        for (const group of this.store.activityGroups) {
            futureTotal += group.planned_count || 0;
        }
        this.store.activityFutureCounter = futureTotal;
    },
});
