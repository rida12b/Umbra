import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import type { ProjectModel } from "../api";
import { machinePlate, projectPlate, roomPlate } from "./plateData.ts";

// The plate of a machine (#79): six fixed slots, filled from the model only. A slot the model has no data for
// is empty (null), never filled with a guess. Real study models: Watchdog v1.7 and the older v1.6 study.

const load = (name: string): ProjectModel =>
  JSON.parse(readFileSync(new URL(`../../test-fixtures/${name}.json`, import.meta.url), "utf-8")) as ProjectModel;

test("a v1.7 machine fills every slot from the model: Contrôle du nom du client", () => {
  const plate = machinePlate(load("watchdog-v17"), "porte-client")!;
  assert.equal(plate.title, "Contrôle du nom du client");
  assert.equal(plate.room, "Porte d'entrée du service");
  assert.equal(plate.fait, "Refuse les demandes sans nom de client");
  assert.deepEqual(plate.recoit, [{ text: "toute demande reçue", refusal: false }, { text: "le nom du client dans l'en-tête", refusal: false }]);
  assert.deepEqual(plate.rend?.map((r) => r.refusal), [false, true]); // « ou un refus si le nom du client manque » in red
  assert.deepEqual(
    plate.reglages?.map((r) => [r.nom, r.fichier, r.lignes?.[0], r.verifie]),
    [
      ["Nom de l'en-tête du client", "watchdog_ai/api/middleware/tenant_auth.py", 33, true],
      ["Code de refus", "watchdog_ai/api/middleware/tenant_auth.py", 35, true],
      ["Message de refus", "watchdog_ai/api/middleware/tenant_auth.py", 35, true],
    ],
  );
  assert.deepEqual(plate.ou.map((o) => [o.quoi, o.verifie]), [["TenantAuthMiddleware.dispatch", true]]);
  assert.deepEqual(plate.vuDans.map((v) => [v.journey, v.step]), [["recevoir-releve", 2], ["recevoir-releve", 3]]);
  assert.deepEqual(plate.mots, [{ simple: "nom du client", code: "X-Tenant-ID / tenant_id" }, { simple: "client", code: "tenant" }]);
});

test("a machine of an older study shows every slot, the v1.7 ones empty, never guessed", () => {
  const plate = machinePlate(load("watchdog"), "auth-tenant")!;
  assert.equal(plate.recoit, null);
  assert.equal(plate.rend, null);
  assert.equal(plate.reglages, null);
  assert.ok(plate.ou.length > 0);
  assert.deepEqual(plate.vuDans.map((v) => [v.journey, v.step]), [["envoi-evenement", 1], ["acces-sans-client", 2]]);
});

test("a room plate lists its machines and every step done in it", () => {
  const plate = roomPlate(load("watchdog-v17"), "api")!;
  assert.equal(plate.title, "Porte d'entrée du service");
  assert.ok(plate.recoit && plate.recoit.length > 0);
  assert.deepEqual(plate.rend?.at(-1), { text: "une réponse ou un refus", refusal: true });
  assert.ok(plate.machines.some((m) => m.id === "porte-client"));
  assert.ok(plate.vuDans.every((v) => v.where !== ""));
  assert.equal(roomPlate(load("watchdog-v17"), "nope"), null);
});

test("the project's settings say which ones the code never reads", () => {
  const rows = projectPlate(load("watchdog-v17"));
  const env = rows.find((r) => r.code === "APP_ENV=development")!;
  assert.deepEqual([env.fichier, env.lignes, env.notRead], [".env.example", [2, 2], true]);
});
