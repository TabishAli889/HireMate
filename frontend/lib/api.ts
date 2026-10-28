/** Error thrown by `apiFetch` with the backend's `detail` message when available. */
export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * Calls the FastAPI backend through the same-origin Next.js proxy
 * (`/api/backend/*`), so the browser never sees BACKEND_URL and CORS never applies.
 */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const isJsonBody = init.body !== undefined && !(init.body instanceof FormData);
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (isJsonBody && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");

  let res: Response;
  try {
    res = await fetch(`/api/backend${path}`, { ...init, headers, cache: "no-store" });
  } catch {
    throw new ApiError("Network error — check your connection and try again.", 0);
  }

  if (!res.ok) {
    let detail = res.statusText || "Request failed";
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Non-JSON error body: keep the status text.
    }
    throw new ApiError(detail, res.status);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
