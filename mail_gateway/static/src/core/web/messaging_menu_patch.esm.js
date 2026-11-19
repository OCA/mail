import {MessagingMenu} from "@mail/core/public_web/messaging_menu";
import {Store} from "@mail/core/common/store_service";
import {Thread} from "@mail/core/common/thread_model";
import {patch} from "@web/core/utils/patch";

// Gateway conversations belong to the "Chats" tab of the messaging menu:
// without this, no tab claims them (same hook as im_livechat for its type).
patch(Store.prototype, {
    tabToThreadType(tab) {
        const threadTypes = super.tabToThreadType(tab);
        if (tab === "chat") {
            threadTypes.push("gateway");
        }
        return threadTypes;
    },
});

patch(MessagingMenu.prototype, {
    get _tabs() {
        const tabs = super._tabs;
        const chatTab = tabs.find((tab) => tab.id === "chat");
        if (chatTab) {
            chatTab.counter += this.store.discuss.gateway.threadsWithCounter.length;
        }
        return tabs;
    },
});

patch(Thread.prototype, {
    setAsDiscussThread(pushState) {
        super.setAsDiscussThread(pushState);
        // Core falls back on "channel" for any type other than chat and group.
        if (this.store.env.services.ui.isSmall && this.channel_type === "gateway") {
            this.store.discuss.activeTab = "chat";
        }
    },
});
