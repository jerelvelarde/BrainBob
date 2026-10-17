import { requireDemoAccess } from "../../../../lib/demo-access";

export const runtime = "nodejs";
export const maxDuration = 300;
export const dynamic = "force-dynamic";

type Context = { params: Promise<{ path: string[] }> };

async function forward(request: Request, context: Context): Promise<Response> {
  const denied = requireDemoAccess(request);
  if (denied) return denied;
  const configured = process.env.BRAINBOB_API_URL;
  let backend: URL;
  try {
    if (process.env.VERCEL === "1" && !configured) throw new Error("missing backend");
    backend = new URL(configured ?? "http://127.0.0.1:3001");
    if (!["http:", "https:"].includes(backend.protocol) || backend.username || backend.password ||
        backend.search || backend.hash || backend.pathname !== "/" ||
        (process.env.VERCEL === "1" && backend.protocol !== "https:")) throw new Error("invalid backend");
  } catch {
    return Response.json({ detail: "Backend URL is not configured correctly." }, { status: 503 });
  }
  const { path } = await context.params;
  if (path.some((part) => part === "." || part === ".." || part.includes("/") || part.includes("\\"))) {
    return Response.json({ detail: "Invalid API path." }, { status: 400 });
  }
  backend.pathname = "/" + path.map(encodeURIComponent).join("/");
  backend.search = new URL(request.url).search;
  const headers = new Headers();
  for (const key of ["authorization", "content-type", "x-brainbob-member", "last-event-id", "sec-fetch-site"]) {
    const value = request.headers.get(key);
    if (value) headers.set(key, value);
  }
  try {
    const response = await fetch(backend, {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : await request.text(),
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(280_000)]),
    });
    // Do not follow redirects with credentials or leak the upstream hostname.
    if (response.status >= 300 && response.status < 400) {
      await response.body?.cancel();
      return Response.json({ detail: "Unexpected backend redirect." }, { status: 502 });
    }
    const outgoing = new Headers({ "Cache-Control": "no-store, no-transform" });
    for (const key of ["content-type", "www-authenticate"]) {
      const value = response.headers.get(key);
      if (value) outgoing.set(key, value);
    }
    // Pass the stream through immediately; cancellation closes the upstream body.
    return new Response(response.body, { status: response.status, headers: outgoing });
  } catch (error) {
    const timeout = error instanceof Error && error.name === "TimeoutError";
    return Response.json({ detail: timeout ? "Backend request timed out. Check its result before retrying a write." : "Backend unavailable." }, {
      status: timeout ? 504 : 502, headers: { "Cache-Control": "no-store" },
    });
  }
}

export const GET = forward;
export const POST = forward;
