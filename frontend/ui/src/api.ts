// Calls to the staff server (frontend/server.py). The browser never talks to the CRM backend directly.

import type { Reply } from "./reply";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

const FALLBACK = "Something went wrong. Please try again.";

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "same-origin",
    });
  } catch {
    throw new ApiError(0, "I couldn't reach the assistant. Please check your connection and try again.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, typeof data.detail === "string" ? data.detail : FALLBACK);
  return data as T;
}

export interface Me {
  name: string;
  must_change: boolean;
}

export const api = {
  me: () => call<Me>("GET", "/me"),
  login: (username: string, password: string) => call<Me>("POST", "/login", { username, password }),
  logout: () => call<{ ok: boolean }>("POST", "/logout"),
  changePassword: (current: string | null, next: string, confirm: string) =>
    call<{ ok: boolean }>("POST", "/password", { current, new: next, confirm }),
  chat: (message: string, conversationId: string) =>
    call<Reply>("POST", "/chat", { message, conversation_id: conversationId }),
  atRisk: () => call<Reply>("GET", "/at-risk"),
  resolve: (updateId: string, confirmed: boolean) =>
    call<{ ok: boolean; text: string }>("POST", `/updates/${encodeURIComponent(updateId)}/${confirmed ? "confirm" : "cancel"}`),
};

/** An id that works on plain-http office networks too, where crypto.randomUUID is unavailable. */
export function newId(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}
