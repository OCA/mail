import {
    Many2ManyCheckboxesField,
    many2ManyCheckboxesField,
} from "@web/views/fields/many2many_checkboxes/many2many_checkboxes_field";
import {onWillUnmount, useState} from "@odoo/owl";
import {CheckBox} from "@web/core/checkbox/checkbox";
import {_t} from "@web/core/l10n/translation";
import {debounce} from "@web/core/utils/timing";
import {getFieldDomain} from "@web/model/relational_model/utils";
import {humanSize} from "@web/core/utils/binary";
import {registry} from "@web/core/registry";
import {useBus} from "@web/core/utils/hooks";
import {useSpecialData} from "@web/views/fields/relational_utils";

/**
 * Picker for the attachments already linked to the record being sent.
 *
 * Same selection semantics as core's ``many2many_checkboxes``, but laid out as
 * a responsive grid behind a foldable header. A record with a long attachment
 * history would otherwise push the composer's Send button off screen.
 */
export class AttachmentCheckboxGrid extends Many2ManyCheckboxesField {
    static template = "mail_attach_existing_attachment.AttachmentCheckboxGrid";
    static components = {CheckBox};

    setup() {
        // Core's setup is deliberately not called. It loads the choices with
        // ``name_search``, whose default limit of 100 silently drops the oldest
        // attachments of a busy record, and it only gets the display name back
        // - too little to tell apart the "image001.png" a mail thread
        // accumulates. Everything else it does is the change bookkeeping
        // replicated below.
        this.state = useState({folded: true});
        this.specialData = useSpecialData((orm, props) => {
            const {relation} = props.record.fields[props.name];
            const domain = getFieldDomain(props.record, props.name, props.domain);
            return orm.call(relation, "search_read", [], {
                context: props.context || {},
                domain,
                fields: ["name", "file_size"],
                order: "id desc",
            });
        });
        this.idsToAdd = new Set();
        this.idsToRemove = new Set();
        this.debouncedCommitChanges = debounce(this.commitChanges.bind(this), 500);
        useBus(
            this.props.record.model.bus,
            "NEED_LOCAL_CHANGES",
            this.commitChanges.bind(this)
        );
        onWillUnmount(this.commitChanges.bind(this));
    }

    /**
     * @returns {Object[]} the attachments linked to the record, newest first.
     */
    get items() {
        return this.specialData.data || [];
    }

    /**
     * @param {Object} attachment
     * @returns {Boolean}
     */
    isSelected(attachment) {
        return this.props.record.data[this.props.name].currentIds.includes(
            attachment.id
        );
    }

    /**
     * @returns {Number} how many attachments are ticked, for the folded header.
     */
    get selectedCount() {
        return this.props.record.data[this.props.name].currentIds.length;
    }

    /**
     * @param {Object} attachment
     * @returns {String} the file size, human readable, or an empty string when
     *  the size is unknown.
     */
    sizeLabel(attachment) {
        return attachment.file_size ? humanSize(attachment.file_size) : "";
    }

    toggleFolded() {
        // Ticking a box only reaches the record after a debounce, so flush
        // before folding: the count in the header has to be the real one.
        this.commitChanges();
        this.state.folded = !this.state.folded;
    }
}

export const attachmentCheckboxGrid = {
    ...many2ManyCheckboxesField,
    component: AttachmentCheckboxGrid,
    displayName: _t("Attachment checkbox grid"),
};

registry.category("fields").add("attachment_checkbox_grid", attachmentCheckboxGrid);
