import {onWillStart, useRef} from "@odoo/owl";
import {user} from "@web/core/user";
import {ActivityMenu} from "@mail/core/web/activity_menu";
import {patch} from "@web/core/utils/patch";

patch(ActivityMenu.prototype, {
    setup() {
        super.setup();
        this.currentFilter = "my";
        this.rootRef = useRef("mail_activity_team_dropdown");
        this.teamActivityCount = 0;

        onWillStart(async () => {
            await this._loadActivities();
        });
    },

    get teamCounter() {
        return this.teamActivityCount;
    },

    activateFilter(filter_el) {
        this.deactivateButtons();
        filter_el.classList.add("active");
        this.currentFilter = filter_el.dataset.filter;
        this.updateTeamActivitiesContext();
        this.store.fetchData({systray_get_activities: true});
        this._loadActivities();
    },

    updateTeamActivitiesContext() {
        var active = false;
        if (this.currentFilter === "team") {
            active = true;
        }
        user.updateContext({team_activities: active});
    },

    onBeforeOpen() {
        user.updateContext({team_activities: false});
        super.onBeforeOpen();
    },

    deactivateButtons() {
        this.rootRef.el.querySelector(".o_filter_nav_item").classList.remove("active");
    },

    onClickActivityFilter(filter) {
        this.activateFilter(this.rootRef.el.querySelector("." + filter));
    },

    async _loadActivities() {
        try {
            // Load team activity count
            const resultTeam = await this.orm.call(
                "mail.activity",
                "get_team_activity_count",
                []
            );
            this.teamActivityCount = resultTeam.team_count || 0;
        } catch (error) {
            console.error("Error loading activities:", error);
        }
    },
});
