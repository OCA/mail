// Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
// License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
// Backported from Odoo 19 (addons/mail).

import {
    SelectionField,
    selectionField,
} from "@web/views/fields/selection/selection_field";
import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {useState} from "@odoo/owl";
import {user} from "@web/core/user";

export class MailServerConfiguratorSelection extends SelectionField {
    static template = "mail_user_outgoing_server.MailServerConfiguratorSelection";

    setup() {
        super.setup();
        this.action = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            value: null,
            connectionFailed: false,
        });
    }

    /**
     * Allow to change the value displayed without making the field dirty.
     */
    get value() {
        return this.state.value || super.value;
    }

    get readonly() {
        return this.props.record.resId !== user.userId;
    }

    get isServerConfigured() {
        return Boolean(this.props.record.data.outgoing_mail_server_id);
    }

    async onOptionChange(value) {
        const oldValue = this.value;
        this.state.value = value;
        await this.props.record.model.root.save();
        try {
            const action = await this.orm.call(
                "res.users",
                "action_setup_outgoing_mail_server",
                [value]
            );
            if (action) {
                this.action.doAction(action);
            }
        } catch (error) {
            this.state.value = oldValue;
            this.notification.add(error.data.message, {
                type: "danger",
            });
        }
    }

    async onTestConnection() {
        await this.props.record.model.root.save();
        try {
            const action = await this.orm.call(
                "res.users",
                "action_test_outgoing_mail_server"
            );
            this.state.connectionFailed = false;
            this.action.doAction(action);
        } catch (error) {
            this.notification.add(_t("Connection failed: %s", error.data.message), {
                type: "danger",
            });
            this.state.connectionFailed = true;
        }
    }
}

registry.category("fields").add("mail_server_configurator_selection", {
    ...selectionField,
    component: MailServerConfiguratorSelection,
});
