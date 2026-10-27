import assert from "node:assert/strict";
import { test } from "node:test";
import { ACTIVITY_VIEW, MAP_VIEW, parseLogin, parseRoute, routeHash } from "./route.ts";

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

test("a Project opens on its map; links made for the old explorer open the map too", () => {
  assert.deepEqual(parseRoute("#/p/shop"), { projectId: "shop", node: MAP_VIEW, box: null });
  assert.deepEqual(parseRoute("#/p/shop?node=x%3Apart%3Aapi&journey=order&step=2"), { projectId: "shop", node: MAP_VIEW, box: null });
  assert.deepEqual(parseRoute("#/p/shop?node=backend%2Fapp%2Fmain.py"), { projectId: "shop", node: MAP_VIEW, box: null });
  assert.deepEqual(parseRoute("#/p/shop?node=activite%3A"), { projectId: "shop", node: ACTIVITY_VIEW, box: null });
  assert.equal(routeHash({ projectId: "shop", node: MAP_VIEW }), "#/p/shop");
  assert.equal(routeHash({ projectId: "shop", node: ACTIVITY_VIEW, box: null }), "#/p/shop?node=activite%3A");
});

test("the inside of a box is a page of its own: Back goes up, a link opens it (#105)", () => {
  assert.deepEqual(parseRoute("#/p/shop?box=server%3Aapi"), { projectId: "shop", node: MAP_VIEW, box: "server:api" });
  assert.equal(routeHash({ projectId: "shop", node: MAP_VIEW, box: "server:api" }), "#/p/shop?box=server%3Aapi");
  assert.deepEqual(parseRoute("#/p/shop?node=activite%3A&box=server%3Aapi"), { projectId: "shop", node: ACTIVITY_VIEW, box: null });
});
