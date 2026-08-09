import {
    MailComposerAttachmentList,
    mailComposerAttachmentList,
} from "@mail/core/web/mail_composer_attachment_list";
import {onWillRender, useState, useSubEnv} from "@odoo/owl";
import {AttachmentList} from "@mail/core/common/attachment_list";
import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";

/**
 * The files the user just added, as thumbnail cards behind a foldable header.
 *
 * Core renders them as a plain list of links. Cards make an image or a PDF
 * recognisable at a glance, which matters once the composer also offers the
 * attachments already on the record: the two sections have to be told apart.
 * Rendering is delegated to the very component the chatter uses, so the cards
 * look and behave exactly like the ones next to a posted message.
 */
export class MailComposerAttachmentThumbnails extends MailComposerAttachmentList {
    static template =
        "mail_attach_existing_attachment.MailComposerAttachmentThumbnails";
    static components = {AttachmentList};

    setup() {
        super.setup();
        // ``AttachmentList`` reads this to offer Remove rather than Download,
        // and to unlink without a confirmation dialog.
        useSubEnv({inComposer: true});
        this.state = useState({folded: false});
        /** @type {import("models").Attachment[]} */
        this.attachments = [];
        onWillRender(() => {
            this.attachments = this.files.map((file) =>
                this.mailStore["ir.attachment"].insert({
                    id: file.id,
                    mimetype: file.mimetype,
                    name: file.name,
                })
            );
        });
    }

    /**
     * @param {import("models").Attachment} attachment
     */
    unlinkAttachment(attachment) {
        return this.onFileRemove(attachment.id);
    }

    toggleFolded() {
        this.state.folded = !this.state.folded;
    }
}

export const mailComposerAttachmentThumbnails = {
    ...mailComposerAttachmentList,
    component: MailComposerAttachmentThumbnails,
    displayName: _t("Composer attachment thumbnails"),
};

registry
    .category("fields")
    .add("mail_composer_attachment_thumbnails", mailComposerAttachmentThumbnails);
