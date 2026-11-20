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
        trigger: ".o_list_table td.o_data_cell:contains('Test Forward')",
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
            trigger: "div[name=forward_thread] input",
            run: "click",
        },
        {
            content: "Select res.partner Model",
            trigger:
                "div.o_select_menu-choices span.o-dropdown-item:contains('Contact')",
            run: "click",
        },
        {
            content: "Select a thread record",
            trigger:
                '.o_field_widget[name="forward_thread"] input.o-autocomplete--input',
            run: "edit forward@example.com",
        },
        {
            content: "Validate thread record",
            trigger:
                '.o_field_widget[name="forward_thread"] .o-autocomplete--dropdown-menu a[role="option"]:contains(Forward)',
            run: "click",
        },
        {
            content: "Select Follower2",
            trigger: ".o_field_widget[name=partner_ids] input",
            run: "edit Follower2",
        },
        {
            content: "Valid Follower2",
            trigger:
                '.modal .o_field_widget[name="partner_ids"] .o-autocomplete--dropdown-menu a[role="option"]:contains(Follower2)',
            run: "click",
        },
        {
            content: "Wait for Follower2 to be added to the recipients",
            trigger:
                '.modal .o_field_widget[name="partner_ids"] .o_tag:contains(Follower2)',
        },
        {
            content: "Send mail",
            trigger: '.modal button.o_mail_send[name="action_send_mail"]:enabled',
            run: "click",
        },
        {
            isActive: ["auto"],
            content: "Wait for the forward dialog to close",
            trigger:
                "body:not(:has(.modal:visible .o_field_widget[name=forward_type]))",
        },
    ],
});
