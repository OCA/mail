/*  Copyright 2024 Tecnativa - Carlos Lopez
    License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
*/
import {registry} from "@web/core/registry";

registry.category("web_tour.tours").add("mail_print.mail_print_tour", {
    url: "/web",
    steps: () => [
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
            run: "edit Mail Print",
        },
        {
            trigger: ".o_searchview_autocomplete .o-dropdown-item.focus",
            content: "Validate search",
            run: "click",
        },
        {
            content: "Open contact",
            trigger: ".o_list_table td[name='display_name']:contains('Mail Print')",
            run: "click",
        },
        {
            content: "Hover a note",
            trigger: "div.o-mail-Message[aria-label='Note']",
            run: "hover",
        },
        {
            content: "Print action is not available",
            trigger: '[name="mail_print"]:not(:visible)',
        },
        {
            content: "Hover a message",
            trigger: "div.o-mail-Message[aria-label='Message']",
            run: "hover",
        },
        {
            content: "Print a message",
            trigger: "[name='mail_print']",
            run: "click",
        },
    ],
});
