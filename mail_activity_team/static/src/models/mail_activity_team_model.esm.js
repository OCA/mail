import {Record} from "@mail/model/export";

export class MailActivityTeam extends Record {
    static _name = "mail.activity.team";

    /** @type {Number} */
    id;
    /** @type {String} */
    name;
}

MailActivityTeam.register();
