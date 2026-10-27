import assert from "node:assert/strict";
import { test } from "node:test";
import { vscodeLink } from "./vscode.ts";

test("a function opens in VS Code at its line, on Windows and elsewhere (#106)", () => {
  assert.equal(
    vscodeLink("C:\\clients\\full-stack-fastapi-template", "backend/app/api/routes/items.py", 14),
    "vscode://file/C:/clients/full-stack-fastapi-template/backend/app/api/routes/items.py:14",
  );
  assert.equal(vscodeLink("/home/me/sqlite-utils/", "sqlite_utils/db.py", 4604), "vscode://file/home/me/sqlite-utils/sqlite_utils/db.py:4604");
  assert.equal(vscodeLink("C:/a b", "x.py", 0), "vscode://file/C:/a%20b/x.py:1"); // « ouvrir le code »: line 1
});
