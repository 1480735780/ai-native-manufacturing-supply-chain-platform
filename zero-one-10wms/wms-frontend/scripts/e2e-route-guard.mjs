import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.resolve(HERE, "..", "..", ".runtime_tmp");
const TOKENS = JSON.parse(fs.readFileSync(path.join(HERE, "..", "..", ".runtime_tmp", "e2e_guard_tokens.json"), "utf8"));
const BASE = "http://127.0.0.1:4173";
const PORT = 9333;
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PROFILE = path.join(OUT_DIR, "chrome-e2e-profile");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function getWs() {
  for (let i = 0; i < 60; i += 1) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      const json = await res.json();
      if (json.webSocketDebuggerUrl) return json.webSocketDebuggerUrl;
    } catch {
      /* not up yet */
    }
    await sleep(500);
  }
  throw new Error("chrome devtools endpoint not ready");
}

class Cdp {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
    ws.addEventListener("message", (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
      }
    });
  }

  send(method, params = {}, sessionId) {
    this.id += 1;
    const id = this.id;
    const payload = { id, method, params };
    if (sessionId) payload.sessionId = sessionId;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify(payload));
    });
  }
}

async function runCase(cdp, role, token) {
  const ctx = await cdp.send("Target.createBrowserContext", { disposeOnDetach: false });
  const contextId = ctx.browserContextId;
  const target = await cdp.send("Target.createTarget", { url: "about:blank", browserContextId: contextId });
  const attached = await cdp.send("Target.attachToTarget", { targetId: target.targetId, flatten: true });
  const sid = attached.sessionId;
  await cdp.send("Page.enable", {}, sid);
  await cdp.send("Runtime.enable", {}, sid);

  await cdp.send("Page.navigate", { url: `${BASE}/` }, sid);
  await sleep(1500);
  await cdp.send(
    "Runtime.evaluate",
    { expression: `localStorage.setItem('token', ${JSON.stringify(token)}); localStorage.getItem('token').length` },
    sid,
  );

  await cdp.send("Page.navigate", { url: `${BASE}/inspection/alerts` }, sid);
  await sleep(4000);
  const probe = await cdp.send(
    "Runtime.evaluate",
    {
      expression: `JSON.stringify({path: location.pathname, text: document.body.innerText.replace(/\\s+/g,' ').slice(0, 260)})`,
      returnByValue: true,
    },
    sid,
  );
  const shot = await cdp.send("Page.captureScreenshot", { format: "png" }, sid);
  const file = path.join(OUT_DIR, `r6_guard_${role}.png`);
  fs.writeFileSync(file, Buffer.from(shot.data, "base64"));
  await cdp.send("Target.disposeBrowserContext", { browserContextId: contextId });
  return { ...JSON.parse(probe.result.value), screenshot: file };
}

async function sidebarGuard(cdp, role, token) {
  const ctx = await cdp.send("Target.createBrowserContext", { disposeOnDetach: false });
  const target = await cdp.send("Target.createTarget", { url: "about:blank", browserContextId: ctx.browserContextId });
  const attached = await cdp.send("Target.attachToTarget", { targetId: target.targetId, flatten: true });
  const sid = attached.sessionId;
  await cdp.send("Page.enable", {}, sid);
  await cdp.send("Runtime.enable", {}, sid);
  await cdp.send("Page.navigate", { url: `${BASE}/` }, sid);
  await sleep(1500);
  await cdp.send("Runtime.evaluate", { expression: `localStorage.setItem('token', ${JSON.stringify(token)})` }, sid);
  await cdp.send("Page.navigate", { url: `${BASE}/home` }, sid);
  await sleep(4000);
  const probe = await cdp.send(
    "Runtime.evaluate",
    {
      expression: `JSON.stringify({path: location.pathname, hasInspection: document.body.innerText.includes('异常巡检'), navItems: document.querySelectorAll('.el-menu-item, .el-sub-menu').length, text: document.body.innerText.replace(/\\s+/g,' ').slice(0, 200)})`,
      returnByValue: true,
    },
    sid,
  );
  const shot = await cdp.send("Page.captureScreenshot", { format: "png" }, sid);
  const file = path.join(OUT_DIR, `r6_menu_${role}.png`);
  fs.writeFileSync(file, Buffer.from(shot.data, "base64"));
  await cdp.send("Target.disposeBrowserContext", { browserContextId: ctx.browserContextId });
  return { ...JSON.parse(probe.result.value), screenshot: file };
}

async function main() {
  fs.mkdirSync(PROFILE, { recursive: true });
  const chrome = spawn(
    CHROME,
    [
      "--headless=new",
      `--remote-debugging-port=${PORT}`,
      `--user-data-dir=${PROFILE}`,
      "--no-first-run",
      "--no-default-browser-check",
      "--disable-gpu",
      "--window-size=1440,900",
      "about:blank",
    ],
    { stdio: "ignore" },
  );
  try {
    const wsUrl = await getWs();
    const ws = new WebSocket(wsUrl);
    await new Promise((resolve, reject) => {
      ws.addEventListener("open", resolve);
      ws.addEventListener("error", reject);
    });
    const cdp = new Cdp(ws);
    const result = { generatedAt: new Date().toISOString(), base: BASE, cases: {} };
    for (const role of ["gly", "cs", "KH"]) {
      const entry = TOKENS[role];
      if (!entry || !entry.token) {
        result.cases[role] = { error: "no token" };
        continue;
      }
      const menu = await sidebarGuard(cdp, role, entry.token);
      const guard = await runCase(cdp, role, entry.token);
      result.cases[role] = { username: entry.username, menu, guard };
      console.log(role, JSON.stringify({ menuPath: menu.path, guardPath: guard.path, hasInspection: menu.hasInspection }));
    }
    const out = path.join(OUT_DIR, "r6_route_guard_result.json");
    fs.writeFileSync(out, JSON.stringify(result, null, 2));
    console.log("saved", out);
  } finally {
    chrome.kill();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
