import { create } from "zustand";

import { streamChat } from "@/lib/chat-client";
import type { ChatMessage } from "@/lib/types";

function getSessionId(): string {
  if (typeof window === "undefined") return "";
  const key = "re-assistant-session-id";
  let id = localStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(key, id);
  }
  return id;
}

type ChatState = {
  messages: ChatMessage[];
  sending: boolean;
  sessionId: string;
  initSession: () => void;
  sendMessage: (text: string) => Promise<void>;
};

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  sending: false,
  sessionId: "",

  initSession: () => {
    if (!get().sessionId) {
      set({ sessionId: getSessionId() });
    }
  },

  sendMessage: async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || get().sending) return;

    const sessionId = get().sessionId || getSessionId();

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text: trimmed,
    };

    const assistantId = crypto.randomUUID();
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: "assistant",
      text: "",
      streaming: true,
      sources: [],
      error: null,
    };

    set((s) => ({
      messages: [...s.messages, userMsg, assistantMsg],
      sending: true,
      sessionId,
    }));

    const patch = (changes: Partial<ChatMessage>) =>
      set((s) => ({
        messages: s.messages.map((m) =>
          m.id === assistantId ? { ...m, ...changes } : m
        ),
      }));

    const appendToken = (chunk: string) =>
      set((s) => ({
        messages: s.messages.map((m) =>
          m.id === assistantId ? { ...m, text: m.text + chunk } : m
        ),
      }));

    try {
      await streamChat(trimmed, sessionId, {
        onEvent: (event) => {
          switch (event.type) {
            case "meta":
              patch({
                intent: event.intent,
                sql: event.sql,
                sources: event.sources,
                rowCount: event.row_count,
                columns: event.columns,
                rows: event.rows,
              });
              break;
            case "token":
              appendToken(event.text);
              break;
            case "error":
              patch({ error: event.message });
              break;
            case "done":
              patch({ latencyMs: event.latency_ms, streaming: false });
              break;
          }
        },
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Something went wrong.";
      patch({ error: msg });
    } finally {
      patch({ streaming: false });
      set({ sending: false });
    }
  },
}));
