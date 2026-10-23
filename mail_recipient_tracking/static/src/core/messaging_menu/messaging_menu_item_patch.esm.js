import {MessagingMenuItem} from "@mail/core/public_web/messaging_menu/messaging_menu_item";
import {patch} from "@web/core/utils/patch";

patch(MessagingMenuItem.prototype, {
    get isMailTrackingFailedTab() {
        return Boolean(
            this.message && this.activeTab().eq(this.store.messagingMenu.failedTab)
        );
    },

    async onClickMailTrackingSetReviewed() {
        await this.message.setMailTrackingReviewed();
    },

    async onClickMailTrackingRetry() {
        await this.message.retryMailTrackingFailedMails();
    },

    /** Activate the pseudo-button with Enter or Space, like a native <button> */
    onKeydownMailTracking(ev, action) {
        if (ev.repeat || (ev.key !== "Enter" && ev.key !== " ")) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        action.call(this);
    },

    get notificationItemProps() {
        const message = this.message;
        if (!this.isMailTrackingFailedTab) {
            return super.notificationItemProps;
        }
        return {
            thread: message.thread,
            message,
            datetime: message.datetime,
            iconSrc: message.authorAvatarUrl,
            important: true,
            isActive: this.isActive(),
            muted: 0,
            textClassName: "text-truncate",
            onSwipeRight: this.hasTouch()
                ? {
                      action: () => message.setMailTrackingReviewed(),
                      icon: "check_circle",
                      bgColor: "bg-success",
                  }
                : undefined,
            onClick: (isMarkAsRead, isMiddleClick) =>
                this.onClick(message, {isMiddleClick}),
        };
    },
});
