import {Chatter} from "@mail/chatter/web_portal/chatter";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(Chatter.prototype, {
    // --------------------------------------------------------------------------
    // Handlers
    // --------------------------------------------------------------------------
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    // eslint-disable-next-line no-unused-vars
    async _onListActivity(ev) {
        if (this.state.thread) {
            const thread = this.state.thread;
            const action = await this.orm.call(
                thread.model,
                "redirect_to_activities",
                [[]],
                {
                    id: this.state.thread.id,
                    model: this.state.thread.model,
                }
            );
            this.action.doAction(action, {
                onClose: () => {
                    thread.refreshActivities();
                    thread.refresh();
                },
            });
        }
    },
});
