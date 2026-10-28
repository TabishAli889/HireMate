import { NextResponse, type NextRequest } from "next/server";

/**
 * Same-origin proxy: /api/backend/<path> → ${BACKEND_URL}/<path>.
 * Keeps BACKEND_URL server-side, avoids CORS, and streams responses (works for SSE).
 */
export const dynamic = "force-dynamic";
export const runtime = "nodejs";
// Agent runs stream for up to a few minutes. 300 s is the Vercel Hobby maximum.
export const maxDuration = 300;

const FORWARD_REQUEST_HEADERS = ["content-type", "accept", "authorization", "x-forwarded-for"];
const FORWARD_RESPONSE_HEADERS = ["content-type", "content-disposition", "cache-control", "retry-after"];

interface RouteContext {
  /** A Promise in Next 15+, a plain object in Next 14; `await` handles both. */
  params: Promise<{ path?: string[] }>;
}

async function proxy(req: NextRequest, context: RouteContext): Promise<Response> {
  const base = process.env.BACKEND_URL;
  if (!base) {
    return NextResponse.json({ detail: "BACKEND_URL is not configured on the server." }, { status: 500 });
  }

  const { path = [] } = await context.params;
  const target = new URL(`${base.replace(/\/+$/, "")}/${path.map(encodeURIComponent).join("/")}`);
  target.search = req.nextUrl.search;

  const headers = new Headers();
  for (const name of FORWARD_REQUEST_HEADERS) {
    const value = req.headers.get(name);
    if (value) headers.set(name, value);
  }

  // Server-side secret: proves to the API that the request came through this proxy.
  const apiKey = process.env.BACKEND_API_KEY;
  if (apiKey) headers.set("x-api-key", apiKey);

  const hasBody = !["GET", "HEAD"].includes(req.method);
  const init: RequestInit & { duplex?: "half" } = {
    method: req.method,
    headers,
    body: hasBody ? req.body : undefined,
    cache: "no-store",
    redirect: "manual",
    signal: req.signal,
  };
  if (hasBody) init.duplex = "half";

  let upstream: Response;
  try {
    upstream = await fetch(target, init);
  } catch {
    return NextResponse.json({ detail: "The HireMate API is unreachable. Please try again shortly." }, { status: 502 });
  }

  const resHeaders = new Headers();
  for (const name of FORWARD_RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) resHeaders.set(name, value);
  }
  if (resHeaders.get("content-type")?.includes("text/event-stream")) {
    resHeaders.set("cache-control", "no-cache, no-transform");
    resHeaders.set("x-accel-buffering", "no");
  }

  return new Response(upstream.body, { status: upstream.status, headers: resHeaders });
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE };
