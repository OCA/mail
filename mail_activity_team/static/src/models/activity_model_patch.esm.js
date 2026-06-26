import {Activity} from "@mail/core/common/activity_model";
import {fields} from "@mail/model/misc";
import {patch} from "@web/core/utils/patch";

patch(Activity.prototype, {
    setup() {
        super.setup(...arguments);
        this.team_id = fields.One("mail.activity.team");
    },
});
