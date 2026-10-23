import {Component, t, useProps} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class MessageTracking extends Component {
    static template = "mail_recipient_tracking.MessageTracking";

    setup() {
        super.setup();
        this.action = useService("action");
        this.props = useProps({
            partner_trackings: t.array(),
            skip_track_links: t.boolean().optional(false),
        });
    }

    onTrackingStatusClick(tracking) {
        if (!tracking.tracking_id) {
            return;
        }
        return this.action.doAction({
            type: "ir.actions.act_window",
            view_mode: "form",
            res_model: "mail.tracking.email",
            views: [[false, "form"]],
            target: "new",
            res_id: tracking.tracking_id,
        });
    }
}
