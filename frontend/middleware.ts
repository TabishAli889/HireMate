import { NextResponse, type NextRequest } from "next/server";

/**
 * Optional password protection for a deployed HireMate (single-user app: your resume lives here).
 * Set SITE_USERNAME and SITE_PASSWORD on the host to turn on browser Basic Auth for every page
 * and API call. Leave them unset locally and nothing changes.
 */
export function middleware(req: NextRequest) {
  const username = process.env.SITE_USERNAME;
  const password = process.env.SITE_PASSWORD;
  if (!username || !password) return NextResponse.next();

  const header = req.headers.get("authorization") ?? "";
  if (header.startsWith("Basic ")) {
    try {
      const decoded = atob(header.slice(6));
      const separator = decoded.indexOf(":");
      if (separator >= 0 && safeEqual(decoded.slice(0, separator), username) && safeEqual(decoded.slice(separator + 1), password)) {
        return NextResponse.next();
      }
    } catch {
      // Malformed header: fall through to the challenge.
    }
  }

  return new NextResponse("Authentication required.", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="HireMate", charset="UTF-8"' },
  });
}

/** Compare without stopping at the first different character (avoids timing hints). */
function safeEqual(a: string, b: string): boolean {
  let diff = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return diff === 0;
}

export const config = {
  // Everything except Next's static assets and the icon.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|icon.svg).*)"],
};
