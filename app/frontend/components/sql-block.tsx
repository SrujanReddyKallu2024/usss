"use client";

import * as React from "react";
import { Check, Copy } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

import { Button } from "@/components/ui/button";

// Syntax-highlighted SQL with a terminal-style header and copy button.
export function SqlBlock({
  sql,
  rowCount,
}: {
  sql: string;
  rowCount?: number | null;
}) {
  const [copied, setCopied] = React.useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">
          SQL query
          {typeof rowCount === "number" && (
            <span className="ml-2 text-muted-foreground/70">
              &middot; {rowCount} {rowCount === 1 ? "row" : "rows"}
            </span>
          )}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 gap-1.5 px-2 text-xs transition-all duration-200"
          onClick={copy}
        >
          {copied ? (
            <>
              <Check className="h-3 w-3 text-green-500" /> Copied!
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" /> Copy
            </>
          )}
        </Button>
      </div>

      {/* Terminal-style code block */}
      <div className="overflow-hidden rounded-lg border border-border/50 shadow-sm">
        {/* Terminal header with dots */}
        <div className="flex items-center gap-1.5 bg-[#1e1e2e] px-3 py-2 border-b border-white/5">
          <span className="terminal-dot" style={{ background: "#ff5f57" }} />
          <span className="terminal-dot" style={{ background: "#febc2e" }} />
          <span className="terminal-dot" style={{ background: "#28c840" }} />
          <span className="ml-3 text-[10px] font-mono text-white/30">SQL</span>
        </div>
        <SyntaxHighlighter
          language="sql"
          style={oneDark}
          customStyle={{
            margin: 0,
            background: "#1e1e2e",
            fontSize: "0.8rem",
            padding: "12px 16px",
            borderRadius: 0,
          }}
          wrapLongLines
        >
          {sql}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}
