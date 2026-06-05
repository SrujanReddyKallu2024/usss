// Shared types matching the backend SSE contract.

export type Intent = "nl2sql" | "rag" | "recommend" | "smalltalk";

export type Source = {
  title: string;
  category: string;
};

// The "meta" event: arrives first, describes how the bot answered.
export type MetaEvent = {
  type: "meta";
  intent: Intent;
  sql: string | null;
  sources: Source[];
  row_count: number | null;
  columns: string[];
  rows: unknown[][];
};

export type TokenEvent = {
  type: "token";
  text: string;
};

export type DoneEvent = {
  type: "done";
  latency_ms: number;
};

export type ErrorEvent = {
  type: "error";
  message: string;
};

export type StreamEvent = MetaEvent | TokenEvent | DoneEvent | ErrorEvent;

// A single message rendered in the chat.
export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  // assistant-only fields, filled from the meta event
  intent?: Intent;
  sql?: string | null;
  sources?: Source[];
  rowCount?: number | null;
  columns?: string[];
  rows?: unknown[][];
  latencyMs?: number | null;
  // streaming/state flags
  streaming?: boolean;
  error?: string | null;
};
