// board.cells.md — serves the shipboard R2 bucket with an index fallback.
export default {
  async fetch(req, env) {
    const path = new URL(req.url).pathname;
    const key = path === "/" ? "index.html" : path.slice(1);
    const obj = await env.SHIPBOARD.get(key);
    if (!obj) return new Response("not found", { status: 404 });
    return new Response(obj.body, {
      headers: {
        "content-type": obj.httpMetadata?.contentType ?? "text/html; charset=utf-8",
        "cache-control": "no-cache",
      },
    });
  },
};
