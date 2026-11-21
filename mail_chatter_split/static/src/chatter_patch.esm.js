import {Chatter} from "@mail/chatter/web_portal_project/chatter";
import {MESSAGE_SEARCH_FILTERS} from "@mail/core/common/search_message_input";
import {browser} from "@web/core/browser/browser";
import {patch} from "@web/core/utils/patch";

export const CHATTER_FILTER_STORAGE_KEY = "mail_chatter_split.chatterFilter";

const FILTER_ICONS = {
    messages: "forum",
    notes: "sticky_note_2",
    activities: "schedule",
    changes: "edit",
};

/**
 * @returns {String|undefined} the remembered `search_filter` (`undefined` = All)
 */
function getStoredFilter() {
    const stored = browser.sessionStorage.getItem(CHATTER_FILTER_STORAGE_KEY);
    return MESSAGE_SEARCH_FILTERS.some((f) => f.id && f.id === stored)
        ? stored
        : undefined;
}

/**
 * @param {String|undefined} filterId
 */
function setStoredFilter(filterId) {
    if (filterId) {
        browser.sessionStorage.setItem(CHATTER_FILTER_STORAGE_KEY, filterId);
    } else {
        browser.sessionStorage.removeItem(CHATTER_FILTER_STORAGE_KEY);
    }
}

/**
 * Tabs on top of the chatter that drive the native (server-side) message
 * filters of the chatter search: All, Messages, Notes, Activities, Changes.
 * The selected tab is remembered while browsing between records.
 *
 * `messageSearch` and `closeSearch` come from `@mail/chatter/web/chatter_patch`.
 */
patch(Chatter.prototype, {
    get chatterSplitFilters() {
        return MESSAGE_SEARCH_FILTERS.map((searchFilter) => ({
            ...searchFilter,
            key: searchFilter.id ?? "all",
            icon: FILTER_ICONS[searchFilter.id] ?? "view_list",
        }));
    },

    /**
     * @param {Object} chatterFilter one of `chatterSplitFilters`
     * @returns {String}
     */
    chatterSplitButtonClass(chatterFilter) {
        return chatterFilter.id === this.chatterSplitActiveFilter
            ? "btn-primary"
            : "btn-outline-secondary";
    },

    get chatterSplitActiveFilter() {
        return this.messageSearch?.search_filter;
    },

    /**
     * Planned activities are shown on the "All" tab (core behaviour) and on
     * the "Activities" tab, unless a search term is entered.
     */
    get chatterSplitShowActivities() {
        return (
            this.chatterSplitActiveFilter === "activities" &&
            !this.messageSearch.searchTerm
        );
    },

    /**
     * @param {String|undefined} filterId `search_filter` value, `undefined` = All
     */
    setChatterSplitFilter(filterId) {
        setStoredFilter(filterId);
        this.applyChatterSplitFilter(filterId);
    },

    /**
     * Changing `search_filter` makes the native message search run again (it
     * is one of its dependencies), or reset when there is no search term.
     *
     * @param {String|undefined} filterId
     */
    applyChatterSplitFilter(filterId) {
        if (!this.messageSearch || filterId === this.messageSearch.search_filter) {
            return;
        }
        this.messageSearch.lastEmptyTerm = undefined;
        this.messageSearch.search_filter = filterId;
    },

    changeThread(threadModel, threadId) {
        const storedFilter = getStoredFilter();
        super.changeThread(...arguments);
        if (!this.messageSearch || threadId === false) {
            return;
        }
        // Core resets the search when switching records (if the search panel
        // is open), keep the selected tab and refetch for the new record.
        setStoredFilter(storedFilter);
        if (storedFilter && storedFilter === this.messageSearch.search_filter) {
            this.messageSearch.messages = [];
            this.messageSearch.searched = false;
            this.messageSearch.lastEmptyTerm = undefined;
            this.messageSearch.run();
        } else {
            this.applyChatterSplitFilter(storedFilter);
        }
    },

    closeSearch() {
        super.closeSearch(...arguments);
        // Closing the search panel resets its filter to "All".
        setStoredFilter(this.messageSearch?.search_filter);
    },
});
