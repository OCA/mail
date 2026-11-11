import {Chatter} from "@mail/chatter/web_portal_project/chatter";
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
        const thread = this.thread();
        if (thread?.id) {
            const action = await this.orm.call(
                thread.model,
                "redirect_to_activities",
                [[]],
                {
                    id: thread.id,
                    model: thread.model,
                }
            );
            return this.action.doAction(action, {
                onClose: () => this.onActivityChanged(thread),
            });
        }
    },
});
