import { Database, FileText, Home, MessageCircle } from "lucide-react";

import { cn } from "@/lib/utils";
import type { Intent } from "@/lib/types";

// Map a backend intent to a friendly label + icon + color for the badge.
const INTENT_META: Record<
  Intent,
  { label: string; icon: typeof Database; className: string }
> = {
  nl2sql: {
    label: "SQL Query",
    icon: Database,
    className: "bg-[hsl(var(--intent-sql)/0.12)] text-[hsl(var(--intent-sql))] border-[hsl(var(--intent-sql)/0.25)]",
  },
  rag: {
    label: "Policy",
    icon: FileText,
    className: "bg-[hsl(var(--intent-rag)/0.12)] text-[hsl(var(--intent-rag))] border-[hsl(var(--intent-rag)/0.25)]",
  },
  recommend: {
    label: "Recommendation",
    icon: Home,
    className: "bg-[hsl(var(--intent-recommend)/0.12)] text-[hsl(var(--intent-recommend))] border-[hsl(var(--intent-recommend)/0.25)]",
  },
  smalltalk: {
    label: "Chat",
    icon: MessageCircle,
    className: "bg-[hsl(var(--intent-smalltalk)/0.12)] text-[hsl(var(--intent-smalltalk))] border-[hsl(var(--intent-smalltalk)/0.25)]",
  },
};

export function IntentBadge({ intent }: { intent: Intent }) {
  const meta = INTENT_META[intent];
  if (!meta) return null;
  const Icon = meta.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium transition-colors",
        meta.className
      )}
    >
      <Icon className="h-3 w-3" />
      {meta.label}
    </span>
  );
}
