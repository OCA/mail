import {FollowerList} from "@mail/core/web/follower_list";
import {patch} from "@web/core/utils/patch";

patch(FollowerList.prototype, {
    onClickAddFollowers() {
        const originalDoAction = this.action.doAction.bind(this.action);
        const saved = this.action;
        this.action = Object.assign(Object.create(this.action), {
            // The web client filters the loadViews context down to `lang` and
            // keys ending with `_view_ref`. We smuggle the followed record's
            // model through under a `_view_ref`-suffixed key so the wizard's
            // `get_view` can apply the per-model follower domain.
            doAction: (action, options) =>
                originalDoAction(
                    {
                        ...action,
                        context: {
                            ...action.context,
                            restrict_follower_res_model_view_ref:
                                this.props.thread.model,
                        },
                    },
                    options
                ),
        });
        try {
            return super.onClickAddFollowers();
        } finally {
            this.action = saved;
        }
    },
});
