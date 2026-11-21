/* Copyright 2026 Fasil
 * License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl). */

import {ACTION_TAGS} from "@mail/core/common/action";
import {_t} from "@web/core/l10n/translation";
import {registerCallAction} from "@mail/discuss/call/common/call_actions";

function getAnnotation(store) {
    return store.env.services["discuss.screen_annotation"];
}

registerCallAction("screen-annotation", {
    condition: ({channel, store}) =>
        channel?.isSelfInCall && Boolean(getAnnotation(store)?.hasSharedScreen),
    name: ({store}) =>
        getAnnotation(store)?.isDrawing
            ? _t("Stop Drawing on Shared Screen")
            : _t("Draw on Shared Screen"),
    isActive: ({store}) => Boolean(getAnnotation(store)?.isDrawing),
    icon: "edit",
    onSelected: ({store}) => getAnnotation(store)?.toggle(),
    // Right after "Share Screen" (sequence 40) in the same group.
    sequence: 45,
    sequenceGroup: 200,
    tags: ({action}) => (action.isActive ? [ACTION_TAGS.SUCCESS] : []),
});
