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
import {imageUrl} from "@web/core/utils/urls";
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
                fields: ["checksum", "file_size", "has_thumbnail", "mimetype", "name"],
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

    /**
     * @param {Object} attachment
     * @returns {String|false} a picture to preview in the tooltip: the image
     *  itself, or the thumbnail Odoo generated for a PDF. Other file types
     *  have nothing worth showing, and asking for one would only serve back a
     *  generic mimetype placeholder.
     */
    previewUrl(attachment) {
        const params = {height: 200, unique: attachment.checksum, width: 300};
        if (attachment.mimetype && attachment.mimetype.startsWith("image/")) {
            return imageUrl("ir.attachment", attachment.id, "datas", params);
        }
        if (attachment.has_thumbnail) {
            return imageUrl("ir.attachment", attachment.id, "thumbnail", params);
        }
        return false;
    }

    /**
     * @param {Object} attachment
     * @returns {String} the tooltip payload, which the tooltip service reads
     *  back out of the DOM as JSON.
     */
    tooltipInfo(attachment) {
        return JSON.stringify({
            name: attachment.name,
            size: this.sizeLabel(attachment),
            src: this.previewUrl(attachment),
        });
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
