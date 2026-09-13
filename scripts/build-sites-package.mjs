import { cp, mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";

const projectRoot = process.cwd();
const viteDist = path.join(projectRoot, "dist", "public");
const sitesRoot = path.join(projectRoot, ".sites-build");
const sitesDist = path.join(sitesRoot, "dist");
const serverDir = path.join(sitesDist, "server");
const clientDir = path.join(sitesDist, "client");
const openAiDir = path.join(sitesDist, ".openai");
const hostingSource = path.join(projectRoot, ".openai", "hosting.json");

const mimeByExtension = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

async function walkFiles(root) {
  const entries = await readdir(root, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const fullPath = path.join(root, entry.name);
    if (entry.isDirectory()) {
      files.push(...await walkFiles(fullPath));
    } else if (entry.isFile()) {
      files.push(fullPath);
    }
  }

  return files;
}

function publicRoute(filePath) {
  const relative = path.relative(viteDist, filePath).split(path.sep).join("/");
  return `/${relative}`;
}

async function buildAssetManifest() {
  const files = await walkFiles(viteDist);
  const assets = {};

  for (const filePath of files) {
    const route = publicRoute(filePath);
    const contents = await readFile(filePath);
    const mime = mimeByExtension[path.extname(filePath)] ?? "application/octet-stream";
    assets[route] = {
      body: contents.toString("base64"),
      mime,
    };
  }

  return assets;
}

function workerSource(assets) {
  return `const ASSETS = ${JSON.stringify(assets)};

function decodeBase64(value) {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

function responseFor(pathname) {
  const asset = ASSETS[pathname] ?? ASSETS["/index.html"];
  return new Response(decodeBase64(asset.body), {
    headers: {
      "cache-control": pathname.includes("/assets/")
        ? "public, max-age=31536000, immutable"
        : "no-store",
      "content-type": asset.mime,
      "x-valo-demo": "simulated-presentation-only",
    },
  });
}

export default {
  async fetch(request) {
    const url = new URL(request.url);

    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method not allowed", { status: 405 });
    }

    if (url.pathname === "/health") {
      return Response.json({
        ok: true,
        demo: "VALO live system simulation",
        disclosure: "presentation only, no production mutations",
      });
    }

    return responseFor(url.pathname);
  },
};
`;
}

await rm(sitesRoot, { recursive: true, force: true });
await mkdir(serverDir, { recursive: true });
await mkdir(clientDir, { recursive: true });
await mkdir(openAiDir, { recursive: true });
await cp(viteDist, clientDir, { recursive: true });
await writeFile(path.join(openAiDir, "hosting.json"), await readFile(hostingSource, "utf8"));
await writeFile(path.join(serverDir, "index.js"), workerSource(await buildAssetManifest()), "utf8");

console.log(`Built Sites package at ${sitesDist}`);
