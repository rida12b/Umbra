import { defineConfig, devices } from "@playwright/test";

const PORT = 7899;

// The real engine on a fixture Project (ui/e2e/server.py); it never runs a model (#114).
export default defineConfig({
  testDir: "e2e",
  timeout: 30_000,
  // One worker: a `show` is shared by every tab of the Project and sends it back to Level 0,
  // so a desktop show test running beside a mobile Level 1 test makes the latter fail (#105 CI).
  workers: 1,
  use: { baseURL: `http://127.0.0.1:${PORT}`, trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: {
    command: `python e2e/server.py ${PORT}`,
    url: `http://127.0.0.1:${PORT}/v1/health`,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
