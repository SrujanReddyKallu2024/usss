
export type Intent = "nl2sql" | "rag" | "recommend" | "smalltalk";

export type Source = {
  title: string;
  category: string;
};

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

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  intent?: Intent;
  sql?: string | null;
  sources?: Source[];
  rowCount?: number | null;
  columns?: string[];
  rows?: unknown[][];
  latencyMs?: number | null;
  streaming?: boolean;
  error?: string | null;
};
