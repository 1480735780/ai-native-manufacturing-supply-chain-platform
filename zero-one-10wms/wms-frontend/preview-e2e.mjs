import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const DIST = path.join(ROOT, "dist-e2e");
const PORT = 4173;
const GATEWAY = { host: "127.0.0.1", port: 10001 };

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
};

function proxy(req, res) {
  const target = req.url.replace(/^\/api/, "") || "/";
  const headers = { ...req.headers, host: `${GATEWAY.host}:${GATEWAY.port}` };
  const upstream = http.request(
    { host: GATEWAY.host, port: GATEWAY.port, path: target, method: req.method, headers },
    (up) => {
      res.writeHead(up.statusCode || 502, up.headers);
      up.pipe(res);
    },
  );
  upstream.on("error", (err) => {
    res.writeHead(502, { "content-type": "application/json" });
    res.end(JSON.stringify({ code: 502, message: `proxy error: ${err.message}` }));
  });
  req.pipe(upstream);
}

const server = http.createServer((req, res) => {
  if (req.url.startsWith("/api")) {
    proxy(req, res);
    return;
  }
  const urlPath = decodeURIComponent(req.url.split("?")[0]);
  let filePath = path.join(DIST, urlPath === "/" ? "index.html" : urlPath);
  if (!filePath.startsWith(DIST)) {
    res.writeHead(403);
    res.end("forbidden");
    return;
  }
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    filePath = path.join(DIST, "index.html");
  }
  const ext = path.extname(filePath).toLowerCase();
  res.writeHead(200, { "content-type": MIME[ext] || "application/octet-stream" });
  fs.createReadStream(filePath).pipe(res);
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`preview-e2e listening on http://127.0.0.1:${PORT} (dist=${DIST}, proxy=/api→${GATEWAY.host}:${GATEWAY.port})`);
});
