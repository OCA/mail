import {Record} from "@mail/model/record";

export class MailActivityTeam extends Record {
    static id = "id";
    static _name = "mail.activity.team";

    /** @type {Number} */
    id;
    /** @type {String} */
    name;
}

MailActivityTeam.register();
