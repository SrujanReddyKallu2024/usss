"use client";

import { AlertCircle, Bot, User } from "lucide-react";
import ReactMarkdown from "react-markdown";

import { DataTable } from "@/components/data-table";
import { DetailsPanel } from "@/components/details-panel";
import { IntentBadge } from "@/components/intent-badge";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/lib/types";

function ThinkingDots() {
  return (
    <span className="inline-flex items-center gap-0.5 py-1">
      <span className="thinking-dot" />
      <span className="thinking-dot" />
      <span className="thinking-dot" />
    </span>
  );
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end gap-3">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-gradient-to-br from-[hsl(var(--primary))] to-[hsl(var(--primary)/0.85)] px-4 py-2.5 text-sm text-primary-foreground shadow-md">
          {message.text}
        </div>
        <Avatar isUser />
      </div>
    );
  }

  const showCaret = message.streaming && !message.error;
  const showThinking = message.streaming && !message.text && !message.error;
  const hasRows = Boolean(message.columns?.length && message.rows?.length);

  return (
    <div className="flex justify-start gap-3">
      <Avatar />
      <div className="max-w-[85%] space-y-1.5">
        {message.intent && (
          <div className="flex">
            <IntentBadge intent={message.intent} />
          </div>
        )}

        <div
          className={cn(
            "rounded-2xl rounded-bl-sm border bg-card/90 backdrop-blur-sm px-4 py-2.5 text-sm shadow-sm transition-all",
            message.error && "border-destructive/50 bg-destructive/10"
          )}
        >
          {message.error ? (
            <div className="flex items-start gap-2 text-destructive">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{message.error}</span>
            </div>
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none leading-relaxed">
              {showThinking ? (
                <ThinkingDots />
              ) : (
                <ReactMarkdown
                  components={{
                    p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                    ul: ({ children }) => <ul className="my-1.5 ml-4 list-disc">{children}</ul>,
                    ol: ({ children }) => <ol className="my-1.5 ml-4 list-decimal">{children}</ol>,
                    li: ({ children }) => <li className="mb-0.5">{children}</li>,
                    strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
                    code: ({ children }) => (
                      <code className="rounded-md bg-muted px-1.5 py-0.5 font-mono text-xs text-accent-foreground">
                        {children}
                      </code>
                    ),
                  }}
                >
                  {message.text}
                </ReactMarkdown>
              )}
              {showCaret && <span className="typing-caret" />}
            </div>
          )}
        </div>

        {!message.error && hasRows && !message.streaming && (
          <div className="animate-fade-in-up rounded-2xl border bg-card/90 backdrop-blur-sm px-4 py-3 shadow-sm">
            <DataTable
              columns={message.columns!}
              rows={message.rows!}
              rowCount={message.rowCount ?? message.rows!.length}
            />
          </div>
        )}

        {!message.error && <DetailsPanel message={message} />}

        {typeof message.latencyMs === "number" && (
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-green-500/70" />
            {(message.latencyMs / 1000).toFixed(1)}s
          </div>
        )}
      </div>
    </div>
  );
}

function Avatar({ isUser = false }: { isUser?: boolean }) {
  return (
    <div
      className={cn(
        "flex h-8 w-8 shrink-0 items-center justify-center rounded-full shadow-sm transition-transform hover:scale-105",
        isUser
          ? "bg-gradient-to-br from-[hsl(var(--primary))] to-[hsl(var(--primary)/0.8)] text-white"
          : "border bg-card text-muted-foreground"
      )}
    >
      {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
    </div>
  );
}
