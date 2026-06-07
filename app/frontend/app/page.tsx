"use client";

import * as React from "react";
import { Building2 } from "lucide-react";

import { Composer } from "@/components/composer";
import { MessageBubble } from "@/components/message-bubble";
import { Suggestions } from "@/components/suggestions";
import { ThemeToggle } from "@/components/theme-toggle";
import { useChatStore } from "@/store/chat-store";

export default function ChatPage() {
  const messages = useChatStore((s) => s.messages);
  const sending = useChatStore((s) => s.sending);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const initSession = useChatStore((s) => s.initSession);

  const bottomRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    initSession();
  }, [initSession]);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const empty = messages.length === 0;

  return (
    <div className="flex h-dvh flex-col bg-background">
      <div className="gradient-accent-line shrink-0" />

      <header className="glass sticky top-0 z-20 flex items-center justify-between border-b border-border/50 px-4 py-3 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-[hsl(var(--primary))] to-[hsl(var(--intent-recommend))] text-white shadow-md">
            <Building2 className="h-4 w-4" />
          </div>
          <div>
            <span className="font-semibold tracking-tight">Real Estate Assistant</span>
            <p className="text-[11px] text-muted-foreground">Powered by AI</p>
          </div>
        </div>
        <ThemeToggle />
      </header>

      <main className="flex-1 overflow-y-auto scroll-smooth">
        <div className="mx-auto w-full max-w-3xl px-4 py-6">
          {empty ? (
            <Suggestions onPick={sendMessage} />
          ) : (
            <div className="space-y-5">
              {messages.map((m, i) => (
                <div
                  key={m.id}
                  className="animate-fade-in-up"
                  style={{ animationDelay: `${Math.min(i * 40, 200)}ms` }}
                >
                  <MessageBubble message={m} />
                </div>
              ))}
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </main>

      <footer className="glass sticky bottom-0 z-20 border-t border-border/50 px-4 py-3 shadow-[0_-2px_20px_-6px_rgba(0,0,0,0.1)]">
        <div className="mx-auto w-full max-w-3xl">
          <Composer onSend={sendMessage} disabled={sending} />
          <p className="mt-2 text-center text-[11px] text-muted-foreground">
            Press Enter to send · Shift+Enter for a new line
          </p>
        </div>
      </footer>
    </div>
  );
}
