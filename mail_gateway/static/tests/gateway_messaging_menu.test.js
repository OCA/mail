import {
    SIZES,
    click,
    contains,
    defineMailModels,
    openDiscuss,
    patchUiSize,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import {describe, expect, test} from "@odoo/hoot";
import {getService} from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

function createFixtures(pyEnv, {unread = false} = {}) {
    pyEnv["discuss.channel"].create({name: "Channel fixture"});
    const channelId = pyEnv["discuss.channel"].create({
        name: "Gateway fixture",
        channel_type: "gateway",
        group_public_id: false,
    });
    if (unread) {
        // The mock server counts unread messages from the member separator.
        pyEnv["mail.message"].create({
            author_id: pyEnv["res.partner"].create({name: "External author"}),
            body: "Unread gateway message",
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    return channelId;
}

test("gateway conversation is listed in the Chats tab", async () => {
    createFixtures(await startServer());
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-MessagingMenu button", {text: "Chats"});
    await contains(".o-mail-MessagingMenu button.fw-bold", {text: "Chats"});
    await contains(".o-mail-NotificationItem", {text: "Gateway fixture"});
    await contains(".o-mail-NotificationItem", {count: 1});
});

test("gateway conversation is not listed in the Channels tab", async () => {
    createFixtures(await startServer());
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-MessagingMenu button", {text: "Channels"});
    await contains(".o-mail-MessagingMenu button.fw-bold", {text: "Channels"});
    await contains(".o-mail-NotificationItem", {text: "Channel fixture"});
    await contains(".o-mail-NotificationItem", {count: 1});
});

test("unread gateway conversation counts in the Chats tab counter", async () => {
    patchUiSize({size: SIZES.SM});
    createFixtures(await startServer(), {unread: true});
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu-tab", {
        text: "Chats",
        contains: [".o-mail-MessagingMenu-tabCounter", {text: "1"}],
    });
    await contains(".o-mail-MessagingMenu-tab", {
        text: "Channels",
        contains: [".o-mail-MessagingMenu-tabCounter", {count: 0}],
    });
});

test("read gateway conversation leaves the Chats tab without counter", async () => {
    patchUiSize({size: SIZES.SM});
    createFixtures(await startServer());
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-MessagingMenu-tab", {text: "Chats"});
    await contains(".o-mail-MessagingMenu-tab.active", {text: "Chats"});
    // Wait for the conversations: a counter could only show up once they are loaded.
    await contains(".o-mail-NotificationItem", {text: "Gateway fixture"});
    await contains(".o-mail-MessagingMenu-tabCounter", {count: 0});
});

test("small screen: opening a gateway conversation activates the Chats tab", async () => {
    patchUiSize({size: SIZES.SM});
    const channelId = createFixtures(await startServer());
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ChatWindow", {text: "Gateway fixture"});
    expect(getService("mail.store").discuss.activeTab).toBe("chat");
});
