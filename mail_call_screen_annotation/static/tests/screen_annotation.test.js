/* Copyright 2026 Fasil
 * License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl). */

import {
    ANNOTATION_MESSAGE_TYPE,
    ANNOTATION_PROTOCOL_VERSION,
    INK_LIFETIME_MS,
    MAX_POINTS_PER_MESSAGE,
    SEND_INTERVAL_MS,
    isValidAnnotationMessage,
} from "@mail_call_screen_annotation/screen_annotation_service.esm";
import {advanceTime, beforeEach, describe, expect, queryFirst, test} from "@odoo/hoot";
import {
    click,
    contains,
    createVideoStream,
    defineMailModels,
    makeMockRtcNetwork,
    mockGetMedia,
    openDiscuss,
    start,
    startServer,
    triggerEvents,
} from "@mail/../tests/mail_test_helpers";
import {getService, patchWithCleanup} from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

beforeEach(() => {
    mockGetMedia();
});

function makeMessage(screenSessionId, values = {}) {
    return {
        type: ANNOTATION_MESSAGE_TYPE,
        version: ANNOTATION_PROTOCOL_VERSION,
        screenSessionId,
        strokeId: 1,
        seq: 1,
        points: [0.1, 0.2, 0.3, 0.4],
        isEnded: false,
        ...values,
    };
}

async function startCallWithSharedScreen() {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({name: "General"});
    const streamerMemberId = pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: pyEnv["res.partner"].create({name: "Streamer"}),
    });
    const env = await start();
    const network = await makeMockRtcNetwork({env, channelId});
    const streamer = network.makeMockRemote(streamerMemberId);
    await openDiscuss(channelId);
    await click("[title='Join Call']");
    await streamer.updateConnectionState("connected");
    await streamer.updateUpload("screen", createVideoStream().getVideoTracks()[0]);
    await contains(".o-discuss-CallParticipantCard[aria-label='Streamer'] video");
    const store = getService("mail.store");
    const annotation = getService("discuss.screen_annotation");
    const receive = (senderId, message) =>
        store.rtc._handleNetworkUpdates({
            detail: {name: "broadcast", payload: {senderId, message}},
        });
    return {annotation, receive, store, streamer};
}

test("mail_call_screen_annotation: drawing mode is toggled from the call actions", async () => {
    const {annotation} = await startCallWithSharedScreen();
    await contains(".o-mail-ScreenAnnotationOverlay:not(.o-isDrawing)");
    expect(annotation.hasSharedScreen).toBe(true);
    // Show the call actions.
    await triggerEvents(".o-discuss-Call-mainCards", ["mousemove"]);
    if (!queryFirst("[name='screen-annotation']")) {
        await click(".o-discuss-CallActionList button[title='More']");
    }
    await click("[name='screen-annotation']");
    await contains(".o-mail-ScreenAnnotationOverlay.o-isDrawing");
    expect(annotation.isDrawing).toBe(true);
    annotation.toggle();
    await contains(".o-mail-ScreenAnnotationOverlay:not(.o-isDrawing)");
});

test("mail_call_screen_annotation: ink of another participant is shown then fades out", async () => {
    const {annotation, receive, streamer} = await startCallWithSharedScreen();
    const screenId = streamer.sessionId;
    await receive(streamer.sessionId, makeMessage(screenId));
    let [stroke] = annotation.getStrokes(screenId);
    expect(stroke.name).toBe("Streamer");
    expect(stroke.points.map(({x, y}) => [x, y])).toEqual([
        [0.1, 0.2],
        [0.3, 0.4],
    ]);
    // Received twice when both the SFU and peer-to-peer deliver it.
    await receive(streamer.sessionId, makeMessage(screenId));
    [stroke] = annotation.getStrokes(screenId);
    expect(stroke.points).toHaveLength(2);
    await receive(
        streamer.sessionId,
        makeMessage(screenId, {seq: 2, points: [], isEnded: true})
    );
    annotation.prune(performance.now() + INK_LIFETIME_MS + 1);
    expect([...annotation.getStrokes(screenId)]).toHaveLength(0);
});

test("mail_call_screen_annotation: messages that are invalid or not about a shared screen are ignored", async () => {
    const {annotation, receive, store, streamer} = await startCallWithSharedScreen();
    const screenId = streamer.sessionId;
    expect(isValidAnnotationMessage(makeMessage(screenId))).toBe(true);
    expect(isValidAnnotationMessage(makeMessage(screenId, {version: 2}))).toBe(false);
    expect(isValidAnnotationMessage(makeMessage(screenId, {points: [0.1]}))).toBe(
        false
    );
    expect(isValidAnnotationMessage(makeMessage(screenId, {points: [0.1, NaN]}))).toBe(
        false
    );
    expect(isValidAnnotationMessage(makeMessage(screenId, {points: "0.1,0.2"}))).toBe(
        false
    );
    expect(
        isValidAnnotationMessage(
            makeMessage(screenId, {
                points: new Array(MAX_POINTS_PER_MESSAGE * 2 + 2).fill(0.5),
            })
        )
    ).toBe(false);
    // Our own session does not share its screen.
    await receive(streamer.sessionId, makeMessage(store.rtc.selfSession.id));
    expect([...annotation.getStrokes(store.rtc.selfSession.id)]).toHaveLength(0);
    // Coordinates out of the frame are kept on its edge.
    await receive(streamer.sessionId, makeMessage(screenId, {points: [-3, 7]}));
    const [stroke] = annotation.getStrokes(screenId);
    expect(stroke.points.map(({x, y}) => [x, y])).toEqual([[0, 1]]);
});

test("mail_call_screen_annotation: local strokes are batched and sent to the call", async () => {
    const {annotation, streamer} = await startCallWithSharedScreen();
    const sent = [];
    patchWithCleanup(annotation, {
        send(message) {
            sent.push(message);
        },
    });
    const screenId = streamer.sessionId;
    annotation.startLocalStroke(screenId, 0.5, 0.5);
    annotation.addLocalPoint(0.6, 0.7);
    expect(sent).toHaveLength(0);
    await advanceTime(SEND_INTERVAL_MS);
    expect(sent).toHaveLength(1);
    expect(sent[0]).toEqual(
        makeMessage(screenId, {
            strokeId: sent[0].strokeId,
            points: [0.5, 0.5, 0.6, 0.7],
        })
    );
    annotation.endLocalStroke();
    expect(sent).toHaveLength(2);
    expect(sent[1].seq).toBe(2);
    expect(sent[1].isEnded).toBe(true);
    expect(sent.every(isValidAnnotationMessage)).toBe(true);
    // The local ink is shown too.
    const [stroke] = annotation.getStrokes(screenId);
    expect(stroke.points).toHaveLength(2);
});
