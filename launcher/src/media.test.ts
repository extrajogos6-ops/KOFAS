import assert from "node:assert/strict";
import test from "node:test";
import { permanentPlaybackFailure } from "./media.ts";

test("pausing a pending play request does not permanently disable the video", () => {
  assert.equal(permanentPlaybackFailure(new DOMException("play interrupted by pause", "AbortError")), false);
});

test("unsupported or undecodable media selects the static fallback", () => {
  assert.equal(permanentPlaybackFailure(new DOMException("unsupported codec", "NotSupportedError")), true);
  assert.equal(permanentPlaybackFailure(new Error("decode failed")), true);
});
