import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "dist");
const port = Number(process.env.PORT || 3000);
const contentTypes = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".ico": "image/x-icon",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
};

createServer(async (request, response) => {
    if (request.method !== "GET" && request.method !== "HEAD") {
        response.writeHead(405, { Allow: "GET, HEAD" }).end();
        return;
    }

    let pathname;
    try {
        pathname = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
    } catch {
        response.writeHead(400).end("Bad request");
        return;
    }

    const filePath = path.resolve(root, `.${pathname}`);
    if (filePath !== root && !filePath.startsWith(`${root}${path.sep}`)) {
        response.writeHead(403).end("Forbidden");
        return;
    }

    let target = filePath;
    try {
        if ((await stat(target)).isDirectory()) target = path.join(target, "index.html");
        var body = await readFile(target);
    } catch {
        if (path.extname(pathname)) {
            response.writeHead(404).end("Not found");
            return;
        }
        target = path.join(root, "index.html");
        try {
            body = await readFile(target);
        } catch {
            response.writeHead(500).end("Application build is missing");
            return;
        }
    }

    const isAsset = pathname.startsWith("/assets/");
    response.writeHead(200, {
        "Content-Type": contentTypes[path.extname(target)] || "application/octet-stream",
        "Content-Length": body.length,
        "Cache-Control": isAsset ? "public, max-age=31536000, immutable" : "no-cache",
        "X-Content-Type-Options": "nosniff",
    });
    response.end(request.method === "HEAD" ? undefined : body);
}).listen(port, "0.0.0.0", () => {
    console.log(`Frontend listening on port ${port}`);
});
