import type { StreamEvent } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Callbacks = {
  onEvent: (event: StreamEvent) => void;
  onClose?: () => void;
};

export async function streamChat(
  message: string,
  sessionId: string,
  callbacks: Callbacks,
  signal?: AbortSignal
): Promise<void> {
  const { onEvent, onClose } = callbacks;

  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
    signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`Request failed: ${res.status} ${res.statusText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith("data:")) continue;

        const payload = trimmed.slice("data:".length).trim();
        if (!payload) continue;

        try {
          const event = JSON.parse(payload) as StreamEvent;
          onEvent(event);
        } catch {
        }
      }
    }

    const last = buffer.trim();
    if (last.startsWith("data:")) {
      const payload = last.slice("data:".length).trim();
      if (payload) {
        try {
          onEvent(JSON.parse(payload) as StreamEvent);
        } catch {
        }
      }
    }
  } finally {
    onClose?.();
  }
}
