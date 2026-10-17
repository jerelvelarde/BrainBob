import { timingSafeEqual } from "node:crypto";

/** A shared gate for fictional demo personas, not per-member authentication. */
export function requireDemoAccess(request: Request): Response | undefined {
  const password = process.env.BRAINBOB_DEMO_PASSWORD;
  if (process.env.VERCEL === "1" && (!password || password.length < 16)) {
    return Response.json({ detail: "Demo access is not configured." }, { status: 503, headers: { "Cache-Control": "no-store" } });
  }
  if (!password) return;
  const [scheme, token = ""] = (request.headers.get("authorization") ?? "").split(" ", 2);
  const actual = Buffer.from(token);
  const expected = Buffer.from(Buffer.from(`brainbob:${password}`).toString("base64"));
  if (scheme.toLowerCase() !== "basic" || actual.length !== expected.length || !timingSafeEqual(actual, expected)) {
    return new Response("Demo access required", { status: 401, headers: {
      "WWW-Authenticate": 'Basic realm="BrainBob demo", charset="UTF-8"', "Cache-Control": "no-store",
    } });
  }
  const origin = request.headers.get("origin");
  if (!["GET", "HEAD", "OPTIONS"].includes(request.method) &&
      (request.headers.get("sec-fetch-site") === "cross-site" || (origin && origin !== new URL(request.url).origin))) {
    return Response.json({ detail: "Cross-origin writes are not allowed." }, { status: 403, headers: { "Cache-Control": "no-store" } });
  }
}
