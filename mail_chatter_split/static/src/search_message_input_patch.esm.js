import {CHATTER_FILTER_STORAGE_KEY} from "./chatter_patch.esm";
import {SearchMessageInput} from "@mail/core/common/search_message_input";
import {browser} from "@web/core/browser/browser";
import {patch} from "@web/core/utils/patch";

patch(SearchMessageInput.prototype, {
    /**
     * Remember a filter picked in the native filter dropdown of the chatter
     * search, so the tabs stay in sync.
     *
     * @override
     */
    onChangeSearchFilter(searchFilter) {
        super.onChangeSearchFilter(...arguments);
        if (!this.env.inChatter) {
            return;
        }
        if (searchFilter.id) {
            browser.sessionStorage.setItem(CHATTER_FILTER_STORAGE_KEY, searchFilter.id);
        } else {
            browser.sessionStorage.removeItem(CHATTER_FILTER_STORAGE_KEY);
        }
    },
});
