"use client";

import * as React from "react";
import { ChevronDown, Code2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { DataTable } from "@/components/data-table";
import { SqlBlock } from "@/components/sql-block";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/lib/types";

export function DetailsPanel({ message }: { message: ChatMessage }) {
  const [open, setOpen] = React.useState(false);

  const hasSql = Boolean(message.sql);
  const hasSources = Boolean(message.sources && message.sources.length > 0);
  if (!hasSql && !hasSources) return null;

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="mt-3">
      <CollapsibleTrigger className="flex items-center gap-1.5 rounded-md px-2 py-1 -ml-2 text-xs font-medium text-muted-foreground transition-all duration-200 hover:text-foreground hover:bg-muted/50">
        <Code2 className="h-3.5 w-3.5" />
        {open ? "Hide details" : "Show details"}
        <ChevronDown
          className={cn(
            "h-3.5 w-3.5 collapsible-chevron"
          )}
          style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)" }}
        />
      </CollapsibleTrigger>

      <CollapsibleContent className="mt-3 space-y-4 animate-fade-in-up rounded-xl border border-border/50 bg-muted/30 backdrop-blur-sm p-4">
        {hasSql && message.columns?.length && message.rows?.length ? (
          <DataTable
            columns={message.columns}
            rows={message.rows}
            rowCount={message.rowCount ?? message.rows.length}
          />
        ) : null}

        {hasSql && (
          <SqlBlock sql={message.sql as string} rowCount={message.rowCount} />
        )}

        {hasSources && (
          <div className="space-y-2">
            <span className="text-xs font-medium text-muted-foreground">
              Policy sources
            </span>
            <div className="flex flex-wrap gap-2">
              {message.sources!.map((src, i) => (
                <Badge
                  key={i}
                  variant="outline"
                  className="gap-1.5 bg-[hsl(var(--intent-rag)/0.08)] border-[hsl(var(--intent-rag)/0.2)] text-[hsl(var(--intent-rag))]"
                >
                  <span className="font-medium">{src.title}</span>
                  <span className="opacity-60">
                    &middot; {src.category}
                  </span>
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}
