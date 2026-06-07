"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableRow,
  TableHead,
  TableHeader,
} from "@/components/ui/table";
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";

type Props = {
  columns: string[];
  rows: unknown[][];
  rowCount: number;
};

const PAGE_SIZE = 5;

function formatCell(value: unknown): string {
  if (value == null) return "";
  const s = String(value);

  const n = Number(s);
  if (!isNaN(n) && s.includes(".") && Math.abs(n) >= 100) {
    return `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return s;
}

function Frame({ className, ...props }: React.ComponentProps<"div">): React.ReactElement {
  return (
    <div
      className={cn(
        "relative flex flex-col rounded-2xl bg-muted/20 p-1 border border-border/50 shadow-sm backdrop-blur-sm",
        "*:[[data-slot=frame-panel]+[data-slot=frame-panel]]:mt-1",
        className
      )}
      data-slot="frame"
      {...props}
    />
  );
}

export function DataTable({ columns, rows, rowCount }: Props) {
  const [currentPage, setCurrentPage] = React.useState(1);

  if (!columns.length || !rows.length) return null;

  const totalPages = Math.ceil(rows.length / PAGE_SIZE);
  const startIndex = (currentPage - 1) * PAGE_SIZE;
  const endIndex = Math.min(startIndex + PAGE_SIZE, rows.length);
  const visibleRows = rows.slice(startIndex, endIndex);

  React.useEffect(() => {
    setCurrentPage(1);
  }, [rows]);

  const maxButtons = 5;
  let startPage = Math.max(1, currentPage - 2);
  let endPage = Math.min(totalPages, startPage + maxButtons - 1);
  if (endPage - startPage < maxButtons - 1) {
    startPage = Math.max(1, endPage - maxButtons + 1);
  }
  const pageNumbers: number[] = [];
  for (let i = startPage; i <= endPage; i++) {
    pageNumbers.push(i);
  }

  const budgetColIndex = columns.findIndex(col => 
    col.toLowerCase().includes("budget") || 
    col.toLowerCase().includes("rent") || 
    col.toLowerCase().includes("payment")
  );
  
  let totalSum: number | null = null;
  if (budgetColIndex !== -1) {
    const sum = rows.reduce((acc, row) => {
      const val = row[budgetColIndex];
      if (val != null) {
        const cleaned = String(val).replace(/[$,]/g, "");
        const num = Number(cleaned);
        if (!isNaN(num)) return acc + num;
      }
      return acc;
    }, 0);
    if (sum > 0) totalSum = sum;
  }

  return (
    <div className="space-y-3 mt-3">
      <div className="flex items-center justify-between px-1">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          Query Results
        </span>
        <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-[hsl(var(--intent-sql))]" />
          {rows.length > PAGE_SIZE
            ? `Showing ${startIndex + 1}-${endIndex} of ${rows.length} rows`
            : `${rows.length} row${rows.length !== 1 ? "s" : ""}`}
        </span>
      </div>

      <Frame className="w-full">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((col) => (
                <TableHead key={col} className={cn(
                  col.toLowerCase().includes("budget") || col.toLowerCase().includes("rent") || col.toLowerCase().includes("amount")
                    ? "text-right"
                    : "text-left"
                )}>
                  {col.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {visibleRows.map((row, ri) => (
              <TableRow key={ri} className="group transition-colors duration-100 hover:bg-muted/30">
                {(row as unknown[]).map((cell, ci) => {
                  const columnName = columns[ci].toLowerCase();
                  const isNumber = columnName.includes("budget") || columnName.includes("rent") || columnName.includes("amount");
                  const isStatus = columnName === "status" || columnName.includes("status");

                  return (
                    <TableCell
                      key={ci}
                      className={cn(
                        "max-w-xs truncate text-[13px]",
                        isNumber ? "text-right font-mono" : "text-left",
                        columnName.includes("name") ? "font-medium" : ""
                      )}
                      title={cell == null ? "null" : String(cell)}
                    >
                      {cell == null ? (
                        <span className="text-muted-foreground/40 italic">—</span>
                      ) : isStatus ? (
                        (() => {
                          const valStr = String(cell);
                          const colorMap: Record<string, string> = {
                            paid: "bg-emerald-500",
                            unpaid: "bg-muted-foreground/64",
                            pending: "bg-amber-500",
                            failed: "bg-red-500",
                            overdue: "bg-red-500",
                            active: "bg-emerald-500",
                            inactive: "bg-muted-foreground/64",
                          };
                          const dotColor = colorMap[valStr.toLowerCase()] || "bg-[hsl(var(--primary))]";
                          return (
                            <span className="relative inline-flex shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-md border border-border/80 bg-background/60 px-2 py-0.5 text-[11px] font-medium text-foreground dark:bg-input/20 shadow-xs">
                              <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${dotColor}`} />
                              {valStr}
                            </span>
                          );
                        })()
                      ) : (
                        formatCell(cell)
                      )}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
          {totalSum !== null && (
            <TableFooter>
              <TableRow>
                {columns.map((col, idx) => {
                  if (idx === 0) {
                    return (
                      <TableCell key={col} className="font-semibold text-muted-foreground" colSpan={budgetColIndex}>
                        Total Sum
                      </TableCell>
                    );
                  }
                  if (idx === budgetColIndex) {
                    return (
                      <TableCell key={col} className="text-right font-mono font-semibold text-foreground">
                        {`$${totalSum.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                      </TableCell>
                    );
                  }
                  if (idx > budgetColIndex) {
                    return <TableCell key={col} />;
                  }
                  return null;
                })}
              </TableRow>
            </TableFooter>
          )}
        </Table>
      </Frame>

      {totalPages > 1 && (
        <div className="flex items-center justify-between px-1 py-1">
          <div className="text-[11px] text-muted-foreground">
            Page {currentPage} of {totalPages}
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage(1)}
              disabled={currentPage === 1}
              className="flex h-7 w-7 items-center justify-center rounded-md border border-border/50 bg-background/50 text-muted-foreground hover:bg-muted/70 disabled:opacity-40 disabled:hover:bg-background/50 transition-colors shadow-xs"
              title="First Page"
            >
              <ChevronsLeft className="h-3.5 w-3.5" />
            </button>

            <button
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="flex h-7 w-7 items-center justify-center rounded-md border border-border/50 bg-background/50 text-muted-foreground hover:bg-muted/70 disabled:opacity-40 disabled:hover:bg-background/50 transition-colors shadow-xs"
              title="Previous Page"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>

            {pageNumbers.map(page => (
              <button
                key={page}
                onClick={() => setCurrentPage(page)}
                className={cn(
                  "flex h-7 w-7 items-center justify-center rounded-md border text-[11px] font-semibold transition-all shadow-xs",
                  currentPage === page
                    ? "border-primary/50 bg-primary/10 text-primary"
                    : "border-border/50 bg-background/50 text-muted-foreground hover:bg-muted/70"
                )}
              >
                {page}
              </button>
            ))}

            <button
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
              className="flex h-7 w-7 items-center justify-center rounded-md border border-border/50 bg-background/50 text-muted-foreground hover:bg-muted/70 disabled:opacity-40 disabled:hover:bg-background/50 transition-colors shadow-xs"
              title="Next Page"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>

            <button
              onClick={() => setCurrentPage(totalPages)}
              disabled={currentPage === totalPages}
              className="flex h-7 w-7 items-center justify-center rounded-md border border-border/50 bg-background/50 text-muted-foreground hover:bg-muted/70 disabled:opacity-40 disabled:hover:bg-background/50 transition-colors shadow-xs"
              title="Last Page"
            >
              <ChevronsRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
