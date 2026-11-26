import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.resolve(HERE, "..", "..", ".runtime_tmp");
const TOKENS = JSON.parse(fs.readFileSync(path.join(OUT_DIR, "e2e_guard_tokens_v2.json"), "utf8"));
const BASE = "http://127.0.0.1:4173";
const PORT = 9334;
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PROFILE = path.join(OUT_DIR, "chrome-e2e-profile-v2");

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function getWs() {
  for (let index = 0; index < 60; index += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      const json = await response.json();
      if (json.webSocketDebuggerUrl) return json.webSocketDebuggerUrl;
    } catch {
      // Chrome is still starting.
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
    this.listeners = new Map();
    ws.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (message.id && this.pending.has(message.id)) {
        const { resolve, reject } = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) reject(new Error(JSON.stringify(message.error)));
        else resolve(message.result);
        return;
      }
      for (const listener of this.listeners.get(message.method) || []) {
        listener(message.params || {}, message.sessionId);
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

  on(method, listener) {
    const listeners = this.listeners.get(method) || [];
    listeners.push(listener);
    this.listeners.set(method, listeners);
  }
}

async function createContext(cdp, token) {
  const context = await cdp.send("Target.createBrowserContext", { disposeOnDetach: false });
  const target = await cdp.send("Target.createTarget", {
    url: "about:blank",
    browserContextId: context.browserContextId,
  });
  const attached = await cdp.send("Target.attachToTarget", {
    targetId: target.targetId,
    flatten: true,
  });
  const sessionId = attached.sessionId;
  await cdp.send("Page.enable", {}, sessionId);
  await cdp.send("Runtime.enable", {}, sessionId);
  await cdp.send(
    "Page.addScriptToEvaluateOnNewDocument",
    { source: `localStorage.setItem('token', ${JSON.stringify(token)});` },
    sessionId,
  );
  await cdp.send("Page.navigate", { url: `${BASE}/` }, sessionId);
  await sleep(1500);
  const tokenProbe = await cdp.send(
    "Runtime.evaluate",
    {
      expression: `JSON.stringify({origin: location.origin, href: location.href, tokenLen: (localStorage.getItem('token') || '').length})`,
      returnByValue: true,
    },
    sessionId,
  );
  if (tokenProbe.exceptionDetails) throw new Error(JSON.stringify(tokenProbe.exceptionDetails));
  return { contextId: context.browserContextId, sessionId, tokenProbe: JSON.parse(tokenProbe.result.value) };
}

async function installMock(cdp, sessionId, endpoint, data) {
  const pattern = `*/login/${endpoint}`;
  await cdp.send("Fetch.enable", { patterns: [{ urlPattern: pattern, requestStage: "Request" }] }, sessionId);
  const body = Buffer.from(JSON.stringify({ code: 10000, data })).toString("base64");
  const listener = async (params, eventSessionId) => {
    if (eventSessionId !== sessionId || !params.request.url.includes(`/login/${endpoint}`)) return;
    await cdp.send(
      "Fetch.fulfillRequest",
      {
        requestId: params.requestId,
        responseCode: 200,
        responseHeaders: [{ name: "Content-Type", value: "application/json" }],
        body,
      },
      sessionId,
    );
    cdp.listeners.set("Fetch.requestPaused", (cdp.listeners.get("Fetch.requestPaused") || []).filter((item) => item !== listener));
  };
  cdp.on("Fetch.requestPaused", listener);
}

async function runCase(cdp, role, token, route, options = {}) {
  const { contextId, sessionId, tokenProbe } = await createContext(cdp, token);
  const debug = [];
  const exceptionHandler = (params) => {
    debug.push({ type: "exception", text: params.exceptionDetails?.text || "exception" });
  };
  const consoleHandler = (params) => {
    debug.push({ type: "console", text: params.args?.map((item) => item.value || item.description || "").join(" ") });
  };
  const responseHandler = (params) => {
    if (/\/api\//.test(params.response?.url || "")) {
      debug.push({ type: "response", url: params.response.url, status: params.response.status });
    }
  };
  const requestHandler = (params) => {
    if (/\/api\//.test(params.request?.url || "")) {
      debug.push({ type: "request", url: params.request.url, method: params.request.method });
    }
  };
  const failedHandler = (params) => {
    debug.push({ type: "networkFailed", error: params.errorText, typeName: params.type });
  };
  cdp.on("Runtime.exceptionThrown", exceptionHandler);
  cdp.on("Runtime.consoleAPICalled", consoleHandler);
  cdp.on("Network.responseReceived", responseHandler);
  cdp.on("Network.requestWillBeSent", requestHandler);
  cdp.on("Network.loadingFailed", failedHandler);
  await cdp.send("Runtime.enable", {}, sessionId);
  await cdp.send("Network.enable", {}, sessionId);
  try {
    if (options.mockEndpoint) {
      await installMock(cdp, sessionId, options.mockEndpoint, options.mockData);
    }
    await cdp.send("Page.navigate", { url: `${BASE}${route}` }, sessionId);
    await sleep(4000);
    const probe = await cdp.send(
      "Runtime.evaluate",
      {
        expression: `JSON.stringify({path: location.pathname, tokenLen: (localStorage.getItem('token') || '').length, resources: performance.getEntriesByType('resource').map((item) => item.name).filter((url) => url.includes('/login/')), text: document.body.innerText.replace(/\\s+/g,' ').slice(0, 320)})`,
        returnByValue: true,
      },
      sessionId,
    );
    const screenshot = await cdp.send("Page.captureScreenshot", { format: "png" }, sessionId);
    const file = path.join(OUT_DIR, `r7_guard_${role}_${options.label || "normal"}.png`);
    fs.writeFileSync(file, Buffer.from(screenshot.data, "base64"));
    return { ...JSON.parse(probe.result.value), screenshot: file, tokenProbe, debug };
  } finally {
    await cdp.send("Target.disposeBrowserContext", { browserContextId: contextId });
  }
}

async function sidebarGuard(cdp, role, token) {
  const { contextId, sessionId } = await createContext(cdp, token);
  try {
    await cdp.send("Page.navigate", { url: `${BASE}/home` }, sessionId);
    await sleep(4000);
    const probe = await cdp.send(
      "Runtime.evaluate",
      {
        expression: `JSON.stringify({path: location.pathname, hasInspection: document.body.innerText.includes('异常巡检'), navItems: document.querySelectorAll('.el-menu-item, .el-sub-menu').length, text: document.body.innerText.replace(/\\s+/g,' ').slice(0, 220)})`,
        returnByValue: true,
      },
      sessionId,
    );
    const screenshot = await cdp.send("Page.captureScreenshot", { format: "png" }, sessionId);
    const file = path.join(OUT_DIR, `r7_menu_${role}.png`);
    fs.writeFileSync(file, Buffer.from(screenshot.data, "base64"));
    return { ...JSON.parse(probe.result.value), screenshot: file };
  } finally {
    await cdp.send("Target.disposeBrowserContext", { browserContextId: contextId });
  }
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
    const result = { generatedAt: new Date().toISOString(), base: BASE, cases: {}, failures: [] };
    const roles = (process.env.E2E_ROLES || "ckjl001,cwtest001,admin").split(",");
    for (const role of roles) {
      const entry = TOKENS[role];
      const menu = await sidebarGuard(cdp, role, entry.token);
      const normal = await runCase(cdp, role, entry.token, "/inspection/alerts");
      const uppercase = await runCase(cdp, role, entry.token, "/Inspection/Alerts", { label: "uppercase" });
      result.cases[role] = { username: entry.username, menu, normal, uppercase };
      const expected = role === "cwtest001" ? "/forbidden" : "/inspection/alerts";
      for (const [label, item] of [["normal", normal], ["uppercase", uppercase]]) {
        if (item.path.toLowerCase() !== expected) result.failures.push(`${role}/${label}: expected ${expected}, got ${item.path}`);
      }
      if (role === "cwtest001" && menu.hasInspection) result.failures.push("cwtest001 menu leaked inspection entry");
      console.log(role, JSON.stringify({ menuPath: menu.path, normalPath: normal.path, uppercasePath: uppercase.path, hasInspection: menu.hasInspection }));
    }

    result.cases.nullUser = await runCase(
      cdp,
      "cwtest001",
      TOKENS.cwtest001.token,
      "/home",
      { label: "null-user", mockEndpoint: "current-user", mockData: null },
    );
    if (result.cases.nullUser.path !== "/forbidden") {
      result.failures.push(`nullUser: expected /forbidden, got ${result.cases.nullUser.path}`);
    }

    result.cases.emptyMenu = await runCase(
      cdp,
      "admin",
      TOKENS.admin.token,
      "/inspection/alerts",
      { label: "empty-menu", mockEndpoint: "get-menus", mockData: [] },
    );
    if (result.cases.emptyMenu.path !== "/forbidden") {
      result.failures.push(`emptyMenu: expected /forbidden, got ${result.cases.emptyMenu.path}`);
    }

    const output = path.join(OUT_DIR, "r7_route_guard_result.json");
    fs.writeFileSync(output, JSON.stringify(result, null, 2));
    console.log("saved", output, "failures", result.failures.length);
    if (result.failures.length > 0) throw new Error(result.failures.join("; "));
  } finally {
    chrome.kill();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
