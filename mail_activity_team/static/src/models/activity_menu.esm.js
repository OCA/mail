import {ActivityMenu} from "@mail/core/web/activity_menu";
import {patch} from "@web/core/utils/patch";
import {proxy} from "@odoo/owl";
import {user} from "@web/core/user";

patch(ActivityMenu.prototype, {
    setup() {
        super.setup();
        this.teamState = proxy({filter: "my"});
    },
    onBeforeOpen() {
        this.teamState.filter = "my";
        user.updateContext({team_activities: false});
        super.onBeforeOpen();
    },
    onClickActivityFilter(filter) {
        this.teamState.filter = filter;
        user.updateContext({team_activities: filter === "team"});
        this.store.fetchStoreData("systray_get_activities");
    },
});
