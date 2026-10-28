import { ApiError } from "@/lib/api";

interface UploadOptions {
  /** Called with 0-100 while the file is being sent. */
  onProgress?: (percent: number) => void;
  signal?: AbortSignal;
  fieldName?: string;
}

/**
 * Multipart upload through the Next.js proxy with real progress events.
 * (fetch() can't report upload progress, so this uses XMLHttpRequest.)
 */
export function uploadFile<T>(path: string, file: File, { onProgress, signal, fieldName = "file" }: UploadOptions = {}): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api/backend${path}`);
    xhr.setRequestHeader("Accept", "application/json");

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100));
    };
    xhr.upload.onload = () => onProgress?.(100);

    xhr.onload = () => {
      let body: unknown = null;
      try {
        body = xhr.responseText ? JSON.parse(xhr.responseText) : null;
      } catch {
        // Non-JSON body; handled below.
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(body as T);
        return;
      }
      const detail = (body as { detail?: unknown } | null)?.detail;
      reject(new ApiError(typeof detail === "string" ? detail : `Upload failed (${xhr.status}).`, xhr.status));
    };
    xhr.onerror = () => reject(new ApiError("Network error — check your connection and try again.", 0));
    xhr.onabort = () => reject(new ApiError("Upload cancelled.", 0));

    if (signal) {
      if (signal.aborted) {
        reject(new ApiError("Upload cancelled.", 0));
        return;
      }
      signal.addEventListener("abort", () => xhr.abort(), { once: true });
    }

    const form = new FormData();
    form.append(fieldName, file);
    xhr.send(form);
  });
}
