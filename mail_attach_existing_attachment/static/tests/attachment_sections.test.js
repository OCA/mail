import {
    click,
    contains,
    defineMailModels,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import {describe, test} from "@odoo/hoot";
import {mountView} from "@web/../tests/web_test_helpers";
import {runAllTimers} from "@odoo/hoot-mock";

describe.current.tags("desktop");
defineMailModels();

const GRID = ".o_attachment_checkbox_grid";
const NEW = ".o_mail_composer_attachment_thumbnails";

/*
 * ``display_object_attachment_ids`` is computed, which the mock server does not
 * do, so the arch below filters on ``res_model`` directly. What the widgets do
 * with the choices they are handed is what these tests are about; the compute
 * itself is covered by the Python tests.
 */
const ARCH = `
    <form>
        <field name="attachment_ids" widget="mail_composer_attachment_thumbnails"/>
        <field name="object_attachment_ids" widget="attachment_checkbox_grid"
               domain="[('res_model', '=', 'res.partner')]"/>
    </form>`;

/**
 * @param {Object} pyEnv
 * @param {String[]} names
 * @returns {Number[]} the ids of attachments linked to a fresh partner
 */
function attachRecordFiles(pyEnv, names) {
    const partnerId = pyEnv["res.partner"].create({name: "Jean Neige"});
    return names.map((name) =>
        pyEnv["ir.attachment"].create({
            file_size: 2048,
            mimetype: "application/pdf",
            name,
            res_id: partnerId,
            res_model: "res.partner",
        })
    );
}

test("available attachments start folded and unfold into a grid", async () => {
    const pyEnv = await startServer();
    attachRecordFiles(pyEnv, ["quote.pdf", "specs.pdf", "photo.pdf"]);
    const composerId = pyEnv["mail.compose.message"].create({});
    await mountView({
        arch: ARCH,
        resId: composerId,
        resModel: "mail.compose.message",
        type: "form",
    });
    await contains(`${GRID} .fa-caret-right`);
    await contains(`${GRID} .badge`, {text: "3"});
    await contains(`${GRID} .o-checkbox`, {count: 0});
    await click(`${GRID} > .cursor-pointer`);
    await contains(`${GRID} .fa-caret-down`);
    await contains(`${GRID}_items .o-checkbox`, {count: 3});
    await contains(`${GRID}_items`, {text: "quote.pdf"});
});

test("folded header counts the ticked attachments", async () => {
    const pyEnv = await startServer();
    attachRecordFiles(pyEnv, ["quote.pdf", "specs.pdf", "photo.pdf"]);
    const composerId = pyEnv["mail.compose.message"].create({});
    await mountView({
        arch: ARCH,
        resId: composerId,
        resModel: "mail.compose.message",
        type: "form",
    });
    await click(`${GRID} > .cursor-pointer`);
    await click(`${GRID}_items .o-checkbox input`);
    await runAllTimers();
    await click(`${GRID} > .cursor-pointer`);
    await contains(`${GRID} .badge`, {text: "1"});
});

test("no available attachments section when the record has none", async () => {
    const pyEnv = await startServer();
    const composerId = pyEnv["mail.compose.message"].create({});
    await mountView({
        arch: ARCH,
        resId: composerId,
        resModel: "mail.compose.message",
        type: "form",
    });
    await contains(".o_form_view");
    await contains(GRID, {count: 0});
});

test("new attachments show as cards, and only once there is one", async () => {
    const pyEnv = await startServer();
    const emptyId = pyEnv["mail.compose.message"].create({});
    await mountView({
        arch: ARCH,
        resId: emptyId,
        resModel: "mail.compose.message",
        type: "form",
    });
    await contains(".o_form_view");
    await contains(NEW, {count: 0});

    const attachmentId = pyEnv["ir.attachment"].create({
        mimetype: "application/pdf",
        name: "draft.pdf",
        res_id: 0,
        res_model: "mail.compose.message",
    });
    const composerId = pyEnv["mail.compose.message"].create({
        attachment_ids: [attachmentId],
    });
    await mountView({
        arch: ARCH,
        resId: composerId,
        resModel: "mail.compose.message",
        type: "form",
    });
    await contains(`${NEW} .o-mail-AttachmentCard`, {text: "draft.pdf"});
    await contains(`${NEW} .badge`, {text: "1"});
    await click(`${NEW} > .cursor-pointer`);
    await contains(`${NEW} .o-mail-AttachmentCard`, {count: 0});
});
