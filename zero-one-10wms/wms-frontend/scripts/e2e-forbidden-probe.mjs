import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");
const OUT_DIR = path.resolve(ROOT, "..", ".runtime_tmp");
const TOKENS = JSON.parse(fs.readFileSync(path.join(OUT_DIR, "e2e_guard_tokens.json"), "utf8"));
const BASE = "http://127.0.0.1:4173";
const PORT = 9334;
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function getWs() {
  for (let i = 0; i < 60; i += 1) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      const json = await res.json();
      if (json.webSocketDebuggerUrl) return json.webSocketDebuggerUrl;
    } catch {
      /* wait */
    }
    await sleep(500);
  }
  throw new Error("devtools not ready");
}

class Cdp {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
    this.events = [];
    ws.addEventListener("message", (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
        return;
      }
      if (msg.method === "Runtime.consoleAPICalled" || msg.method === "Runtime.exceptionThrown") {
        this.events.push(msg);
      }
    });
  }
  send(method, params = {}, sessionId) {
    this.id += 1;
    const payload = { id: this.id, method, params };
    if (sessionId) payload.sessionId = sessionId;
    return new Promise((resolve, reject) => {
      this.pending.set(this.id, { resolve, reject });
      this.ws.send(JSON.stringify(payload));
    });
  }
}

async function main() {
  const chrome = spawn(
    CHROME,
    [
      "--headless=new",
      `--remote-debugging-port=${PORT}`,
      `--user-data-dir=${path.join(OUT_DIR, "chrome-probe-profile")}`,
      "--no-first-run",
      "--no-default-browser-check",
      "--disable-gpu",
      "about:blank",
    ],
    { stdio: "ignore" },
  );
  try {
    const wsUrl = await getWs();
    const ws = new WebSocket(wsUrl);
    await new Promise((res, rej) => {
      ws.addEventListener("open", res);
      ws.addEventListener("error", rej);
    });
    const cdp = new Cdp(ws);
    const out = {};
    for (const role of ["cs", "gly"]) {
      const token = TOKENS[role].token;
      const ctx = await cdp.send("Target.createBrowserContext", { disposeOnDetach: false });
      const t = await cdp.send("Target.createTarget", { url: "about:blank", browserContextId: ctx.browserContextId });
      const att = await cdp.send("Target.attachToTarget", { targetId: t.targetId, flatten: true });
      const sid = att.sessionId;
      await cdp.send("Page.enable", {}, sid);
      await cdp.send("Runtime.enable", {}, sid);
      await cdp.send("Page.navigate", { url: `${BASE}/` }, sid);
      await sleep(1500);
      await cdp.send("Runtime.evaluate", { expression: `localStorage.setItem('token', ${JSON.stringify(token)})` }, sid);
      await cdp.send("Page.navigate", { url: `${BASE}/forbidden` }, sid);
      await sleep(5000);
      const probe = await cdp.send(
        "Runtime.evaluate",
        {
          expression: `JSON.stringify({path: location.pathname, hasCode: !!document.querySelector('.code'), code: (document.querySelector('.code')||{}).textContent || '', info: (document.querySelector('.info')||{}).textContent || '', bodyLen: document.body.innerHTML.length})`,
          returnByValue: true,
        },
        sid,
      );
      out[role] = JSON.parse(probe.result.value);
      out[role].events = cdp.events.slice(-6).map((e) => ({ method: e.method, text: JSON.stringify(e.params).slice(0, 300) }));
      cdp.events = [];
      await cdp.send("Target.disposeBrowserContext", { browserContextId: ctx.browserContextId });
      console.log(role, JSON.stringify(out[role]));
    }
    const file = path.join(OUT_DIR, "r6_forbidden_direct_probe.json");
    fs.writeFileSync(file, JSON.stringify({ generatedAt: new Date().toISOString(), cases: out }, null, 2));
    console.log("saved", file);
  } finally {
    chrome.kill();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
