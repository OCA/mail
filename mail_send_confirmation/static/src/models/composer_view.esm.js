import {Composer} from "@mail/core/common/composer";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(Composer.prototype, {
    /**
     * Ask for confirmation before sending a message (not a note) to the
     * followers of a record. Editing an existing message is not affected.
     *
     * @override
     */
    async sendMessage() {
        if (this.props.type === "message" && !this.props.composer.message) {
            const {promise, resolve} = Promise.withResolvers();
            // Closing the dialog (Esc, ×) triggers `cancel` as well.
            this.store.env.services.dialog.add(ConfirmationDialog, {
                body: _t(
                    "This message will be sent to external partners as well. Are you sure you would like to send this message?"
                ),
                confirmLabel: _t("Send"),
                confirm: () => resolve(true),
                cancel: () => resolve(false),
            });
            if (!(await promise)) {
                return false;
            }
        }
        return super.sendMessage(...arguments);
    },
});
