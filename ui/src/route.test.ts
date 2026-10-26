import assert from "node:assert/strict";
import { test } from "node:test";
import { parseLogin } from "./route.ts";

// The login link of `umbra-engine start` (#98) lands on the Project it just registered.

test("a plain login link lands on the Project list", () => {
  assert.deepEqual(parseLogin("#login=abc_-12"), { code: "abc_-12", landing: "#/" });
});

test("a login link with a Project lands on that Project, its id encoded", () => {
  assert.deepEqual(parseLogin("#login=abc&p=watchdog-1a2b"), { code: "abc", landing: "#/p/watchdog-1a2b" });
  assert.deepEqual(parseLogin("#login=abc&p=proj%C3%A9%20x"), { code: "abc", landing: "#/p/proj%C3%A9%20x" });
});

test("anything else is not a login link; a broken code is no code", () => {
  assert.equal(parseLogin("#/p/x"), null);
  assert.deepEqual(parseLogin("#login=%E0"), { code: null, landing: "#/" });
  assert.deepEqual(parseLogin("#login=&p="), { code: null, landing: "#/" });
});
