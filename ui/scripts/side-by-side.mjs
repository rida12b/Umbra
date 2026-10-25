// The honest side-by-side image of a validated mockup and the real screen (skill interface-ia, « Contrat
// visuel »): same project data, same width, same theme, same state, no banner the mockup does not have.
//
// Usage: node scripts/side-by-side.mjs <design folder> <app base URL> <login code> <out folder>
//   design folder: holds ref-<screen>-<state>.png and pairs.json
//   pairs.json: [{ "name": "floor", "ref": "ref-floor-watchdog.png", "path": "#/p/<project>" }, …]
// Writes <out>/<name>.png (the screen alone) and <out>/<name>-side-by-side.png (mockup | screen).

import { readFileSync, mkdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { chromium } from "@playwright/test";

const [designDir, base, code, outDir] = process.argv.slice(2);
if (!designDir || !base || !code || !outDir) {
  console.error("usage: node scripts/side-by-side.mjs <design folder> <app base URL> <login code> <out folder>");
  process.exit(2);
}
const pairs = JSON.parse(readFileSync(join(designDir, "pairs.json"), "utf-8"));
mkdirSync(outDir, { recursive: true });

// Show the scrollbars, as Chrome on Windows does and as the refs were shot: Playwright hides them by default,
// and a 17 px scrollbar is enough to wrap a layout that fits without it.
const browser = await chromium.launch({ ignoreDefaultArgs: ["--hide-scrollbars"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, colorScheme: "dark" });
await page.goto(`${base}/#login=${code}`);
await page.waitForURL(/#\/$/);
await page.evaluate(() => localStorage.setItem("umbra-theme", "dark")); // the mockups are dark

for (const pair of pairs) {
  await page.goto(`${base}/?shot=${pair.name}${pair.path}`);
  await page.waitForTimeout(1500); // layout, fonts, the room's opening animation
  // The mockup has no « Nouvelle méthode d'étude » banner: hide it so both images show the same frame.
  await page.addStyleTag({ content: '[aria-label="Nouvelle méthode d\'étude"]{display:none!important}' });
  await page.waitForTimeout(200);
  const screen = resolve(outDir, `${pair.name}.png`);
  await page.screenshot({ path: screen });
  // A page set from memory may not read local files: the two images go in as data.
  const asData = (file) => `data:image/png;base64,${readFileSync(file).toString("base64")}`;
  const ref = asData(resolve(designDir, pair.ref));
  const sheet = await browser.newPage({ viewport: { width: 2 * 1440 + 24, height: 900 + 44 } });
  await sheet.setContent(`<body style="margin:0;background:#111;font:600 15px system-ui;color:#ddd">
    <div style="display:flex;gap:24px"><div><p style="margin:12px">Maquette validée</p><img src="${ref}" width="1440"></div>
    <div><p style="margin:12px">Écran réel</p><img src="${asData(screen)}" width="1440"></div></div></body>`);
  await sheet.waitForLoadState("load");
  await sheet.screenshot({ path: resolve(outDir, `${pair.name}-side-by-side.png`), fullPage: true });
  await sheet.close();
  console.log(`${pair.name}: ${screen}`);
}
await browser.close();
