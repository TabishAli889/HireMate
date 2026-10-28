import { ApiError } from "@/lib/api";

export interface SSEMessage {
  event: string;
  data: unknown;
}

/** Parse one SSE block ("event: x\ndata: {...}"). Comment lines (":") are keep-alives and ignored. */
export function parseSSEBlock(block: string): SSEMessage | null {
  let event = "message";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (!line || line.startsWith(":")) continue;
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    if (field === "event") event = value;
    else if (field === "data") data.push(value);
  }
  if (data.length === 0) return null;
  try {
    return { event, data: JSON.parse(data.join("\n")) };
  } catch {
    return null;
  }
}

/**
 * POST a JSON body and read a Server-Sent Events response through the Next.js proxy.
 * (EventSource only supports GET, so this reads the fetch stream directly.)
 * Non-stream responses (validation, rate limit, missing API key) throw an ApiError with the backend's message.
 */
export async function postEventStream(
  path: string,
  body: unknown,
  onMessage: (message: SSEMessage) => void,
  signal?: AbortSignal,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`/api/backend${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(body),
      signal,
      cache: "no-store",
    });
  } catch {
    if (signal?.aborted) throw new ApiError("Stopped.", 0);
    throw new ApiError("Network error — check your connection and try again.", 0);
  }

  const contentType = res.headers.get("content-type") ?? "";
  if (!res.ok || !contentType.includes("text/event-stream") || !res.body) {
    let detail = `Request failed (${res.status}).`;
    try {
      const json = (await res.json()) as { detail?: unknown };
      if (typeof json.detail === "string") detail = json.detail;
    } catch {
      // Non-JSON error body: keep the generic message.
    }
    throw new ApiError(detail, res.status);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n?/g, "\n");
      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const message = parseSSEBlock(buffer.slice(0, boundary));
        buffer = buffer.slice(boundary + 2);
        if (message) onMessage(message);
        boundary = buffer.indexOf("\n\n");
      }
    }
    const tail = parseSSEBlock(buffer.trim());
    if (tail) onMessage(tail);
  } catch {
    if (signal?.aborted) throw new ApiError("Stopped.", 0);
    throw new ApiError("The connection was interrupted. Please try again.", 0);
  }
}
