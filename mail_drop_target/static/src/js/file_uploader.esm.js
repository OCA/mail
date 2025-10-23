/* @odoo-module */
import {AttachmentUploadService} from "@mail/core/common/attachment_upload_service";
import {Chatter} from "@mail/chatter/web_portal/chatter";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(AttachmentUploadService.prototype, {
    async _processLoaded(thread, composer, attachmentData, tmpId, def) {
        if (attachmentData.email_upload === 1) {
            this._fileUploadBus.trigger("REFRESH_CHATTER", thread.id);
        } else {
            return super._processLoaded(thread, composer, attachmentData, tmpId, def);
        }
    },
});

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);

        this.attachmentUploadService = useService("mail.attachment_upload");

        this.attachmentUploadService._fileUploadBus.addEventListener(
            "REFRESH_CHATTER",
            ({detail: threadId}) => {
                if (this.state.thread?.id === threadId) {
                    this.reloadParentView();
                }
            }
        );
    },
});
