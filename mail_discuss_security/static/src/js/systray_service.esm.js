import {registry} from "@web/core/registry";
import {user} from "@web/core/user";

const SYSTRAY_REGISTRY = registry.category("systray");
const MESSAGING_MENU_KEY = "mail.messaging_menu";
const DISCUSS_GROUP = "mail_discuss_security.group_discuss";

export const mailDiscussSecuritySystrayService = {
    async start() {
        // Hide the messaging menu (systray) for users not in the group.
        // Removing the entry triggers an UPDATE event on the systray
        // registry, so the navbar re-renders without it.
        const hasGroup = await user.hasGroup(DISCUSS_GROUP);
        if (!hasGroup && SYSTRAY_REGISTRY.contains(MESSAGING_MENU_KEY)) {
            SYSTRAY_REGISTRY.remove(MESSAGING_MENU_KEY);
        }
    },
};

registry
    .category("services")
    .add("mail_discuss_security.systray", mailDiscussSecuritySystrayService);
