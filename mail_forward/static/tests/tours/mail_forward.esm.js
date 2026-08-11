import {registry} from "@web/core/registry";

const contact_steps = [
    {
        trigger: ".o_navbar_apps_menu button",
        run: "click",
    },
    {
        trigger: '.o_app[data-menu-xmlid="contacts.menu_contacts"]',
        run: "click",
    },
    {
        content: "Search Contact",
        trigger: ".o_searchview_input",
        run: "edit Test Forward",
    },
    {
        trigger: ".dropdown-item:contains('Test Forward')",
        content: "Validate search",
        run: "click",
    },
    {
        content: "Switch to list view",
        trigger: ".o_list",
        run: "click",
    },
    {
        content: "Open contact",
        trigger: ".o_list_table td[name='display_name']:contains('Test Forward')",
        run: "click",
    },
];
registry.category("web_tour.tours").add("mail_forward.mail_forward_tour", {
    url: "/web",
    steps: () => [
        ...contact_steps,
        {
            content: "Hover a message to show actions",
            trigger: "div.o-mail-Message[aria-label='Message']",
            run: "hover",
        },
        {
            content: "Click message options button",
            trigger: "button.o-mail-ActionList-button.dropdown-toggle",
            run: "click",
        },
        {
            content: "Forward a message",
            trigger: "button[name=forward]",
            run: "click",
        },
        {
            content: "Select a Forward",
            trigger: ".o_field_widget[name=partner_ids] input",
            run: "edit Forward",
        },
        {
            content: "Valid Forward",
            trigger: ".ui-menu-item a:contains(Forward)",
            run: "click",
        },
        {
            content: "Send mail",
            trigger: "button.o_mail_send",
            run: "click",
        },
        {
            content: "Check Mail Forward",
            trigger:
                "div.o-mail-Message[aria-label='Message']:contains(---------- Forwarded message ---------)",
        },
    ],
});

registry.category("web_tour.tours").add("mail_forward.mail_another_thread_tour", {
    url: "/web",
    steps: () => [
        ...contact_steps,
        {
            content: "Hover a message to show actions",
            trigger: "div.o-mail-Message[aria-label='Message']",
            run: "hover",
        },
        {
            content: "Click message options button",
            trigger: "button.o-mail-ActionList-button.dropdown-toggle",
            run: "click",
        },
        {
            content: "Forward a message",
            trigger: "button[name=forward]",
            run: "click",
        },
        {
            content: "Select the Forward type",
            trigger: "div[name=forward_type] input[data-value=another_thread]",
            run: "click",
        },
        {
            content: "Select the Forward thread",
            trigger: "div[name=forward_thread] select",
            run: "select res.partner",
        },
        {
            content: "Select a thread record",
            trigger: "div[name=forward_thread] input",
            run: "edit forward@example.com",
        },
        {
            content: "Validate thread record",
            trigger: ".ui-menu-item a:contains(Forward)",
            run: "click",
        },
        {
            content: "Select Follower2",
            trigger: ".o_field_widget[name=partner_ids] input",
            run: "edit Follower2",
        },
        {
            content: "Valid Follower2",
            trigger: ".ui-menu-item a:contains(Follower2)",
            run: "click",
        },
        {
            content: "Send mail",
            trigger: "button.o_mail_send",
            run: "click",
        },
        {
            isActive: ["auto"],
            trigger: "body:not(.modal-open)",
            run: "click",
        },
    ],
});
