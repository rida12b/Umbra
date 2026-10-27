import assert from "node:assert/strict";
import { test } from "node:test";
import { commonAddress, shortAddress } from "./addresses.ts";

test("routes under one address show the rest of it only; one route shows it whole (#106)", () => {
  const under = commonAddress(["/api/v1/login/access-token", "/api/v1/users/me"]);
  assert.equal(under, "/api/v1/");
  assert.equal(shortAddress("/api/v1/login/access-token", under), "…/login/access-token");
  assert.equal(commonAddress(["/api/v1/items/"]), "");
  assert.equal(shortAddress("/api/v1/items/", ""), "/api/v1/items/");
  assert.equal(commonAddress(["/a", "/b"]), ""); // nothing shared but the root
});
