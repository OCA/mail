import {Record} from "@mail/core/common/record";

export class MailActivityTeam extends Record {
    static _name = "mail.activity.team";
    /** @type {String} */
    name;
}

MailActivityTeam.register();
