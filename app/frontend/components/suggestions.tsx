"use client";

import { Database, FileText, Home, CalendarClock, Sparkles } from "lucide-react";

// Starter prompts shown on the empty state. Clicking one sends it.
const STARTERS = [
  {
    icon: Database,
    label: "Data Query",
    prompt: "Which tenants have overdue payments?",
    color: "hsl(var(--intent-sql))",
  },
  {
    icon: FileText,
    label: "Policy Lookup",
    prompt: "What is the late payment policy?",
    color: "hsl(var(--intent-rag))",
  },
  {
    icon: Home,
    label: "Recommendation",
    prompt: "Recommend 2 bedroom properties in Austin under 2000",
    color: "hsl(var(--intent-recommend))",
  },
  {
    icon: CalendarClock,
    label: "Analytics",
    prompt: "Show leases expiring in the next 60 days",
    color: "hsl(var(--intent-sql))",
  },
];

export function Suggestions({
  onPick,
}: {
  onPick: (prompt: string) => void;
}) {
  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center gap-8 py-16 text-center">
      {/* Hero icon */}
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-[hsl(var(--primary))] to-[hsl(var(--intent-recommend))] text-white shadow-lg animate-fade-in-up">
        <Sparkles className="h-8 w-8" />
      </div>

      <div className="space-y-2 animate-fade-in-up" style={{ animationDelay: "80ms" }}>
        <h2 className="text-2xl font-bold tracking-tight">Real Estate Assistant</h2>
        <p className="text-sm text-muted-foreground max-w-md">
          Ask about tenants, payments, policies, or get personalized property recommendations.
        </p>
      </div>

      {/* Suggestion cards */}
      <div className="grid w-full gap-3 sm:grid-cols-2">
        {STARTERS.map((item, i) => {
          const Icon = item.icon;
          return (
            <button
              key={item.prompt}
              onClick={() => onPick(item.prompt)}
              className={`animate-fade-in-up animate-stagger-${i + 1} group relative flex items-start gap-3 rounded-xl border border-border/60 bg-card/80 backdrop-blur-sm p-4 text-left transition-all duration-200 hover:border-[hsl(var(--primary)/0.4)] hover:shadow-md hover:-translate-y-0.5`}
            >
              <div
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-transform duration-200 group-hover:scale-110"
                style={{ backgroundColor: `${item.color}15`, color: item.color }}
              >
                <Icon className="h-4 w-4" />
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-0.5">{item.label}</p>
                <p className="text-sm text-foreground">{item.prompt}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
