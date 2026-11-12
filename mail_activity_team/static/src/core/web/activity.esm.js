import {Activity} from "@mail/core/web/activity";
import {patch} from "@web/core/utils/patch";

patch(Activity.prototype, {
    get tooltipInfo() {
        const info = JSON.parse(super.tooltipInfo);
        info.activity.team_id_name = this.activity().team_id?.name;
        return JSON.stringify(info);
    },
});
