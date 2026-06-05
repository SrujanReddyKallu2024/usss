"use client";

import { mergeProps } from "@base-ui/react/merge-props";
import { useRender } from "@base-ui/react/use-render";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import type React from "react";
import {
  Table, TableBody, TableCell,
  TableFooter, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

// Badge
const badgeVariants = cva(
  "relative inline-flex shrink-0 items-center justify-center gap-1 whitespace-nowrap rounded-sm border border-transparent font-medium outline-none transition-shadow disabled:pointer-events-none disabled:opacity-64",
  {
    defaultVariants: { size: "default", variant: "default" },
    variants: {
      size: { default: "h-5.5 min-w-5.5 px-[calc(--spacing(1)-1px)] text-sm sm:h-4.5 sm:min-w-4.5 sm:text-xs" },
      variant: { outline: "border-input bg-background text-foreground dark:bg-input/32" },
    },
  },
);
interface BadgeProps extends useRender.ComponentProps<"span"> {
  variant?: VariantProps<typeof badgeVariants>["variant"];
  size?: VariantProps<typeof badgeVariants>["size"];
}
function Badge({ className, variant, size, render, ...props }: BadgeProps): React.ReactElement {
  return useRender({ defaultTagName: "span", props: mergeProps<"span">({ className: cn(badgeVariants({ className, size, variant })), "data-slot": "badge" }, props), render });
}

// Frame
function Frame({ className, ...props }: React.ComponentProps<"div">): React.ReactElement {
  return (
    <div
      className={cn("relative flex flex-col rounded-2xl bg-muted/72 p-1", "*:[[data-slot=frame-panel]+[data-slot=frame-panel]]:mt-1", className)}
      data-slot="frame"
      {...props}
    />
  );
}

const projects = [
  { name: "Website Redesign", status: "Paid", statusColor: "bg-emerald-500", team: "Frontend Team", budget: "$12,500" },
  { name: "Mobile App", status: "Unpaid", statusColor: "bg-muted-foreground/64", team: "Mobile Team", budget: "$8,750" },
  { name: "API Integration", status: "Pending", statusColor: "bg-amber-500", team: "Backend Team", budget: "$5,200" },
  { name: "Database Migration", status: "Paid", statusColor: "bg-emerald-500", team: "DevOps Team", budget: "$3,800" },
  { name: "User Dashboard", status: "Paid", statusColor: "bg-emerald-500", team: "UX Team", budget: "$7,200" },
  { name: "Security Audit", status: "Failed", statusColor: "bg-red-500", team: "Security Team", budget: "$2,100" },
];

export default function Particle() {
  return (
    <div className="flex items-center justify-center w-full min-h-screen bg-background p-8">
      <Frame className="w-full max-w-2xl">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Project</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Team</TableHead>
              <TableHead className="text-right">Budget</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {projects.map((p) => (
              <TableRow key={p.name}>
                <TableCell className="font-medium">{p.name}</TableCell>
                <TableCell>
                  <Badge variant="outline">
                    <span aria-hidden="true" className={`size-1.5 rounded-full ${p.statusColor}`} />
                    {p.status}
                  </Badge>
                </TableCell>
                <TableCell>{p.team}</TableCell>
                <TableCell className="text-right">{p.budget}</TableCell>
              </TableRow>
            ))}
          </TableBody>
          <TableFooter>
            <TableRow>
              <TableCell colSpan={3}>Total Budget</TableCell>
              <TableCell className="text-right">$39,550</TableCell>
            </TableRow>
          </TableFooter>
        </Table>
      </Frame>
    </div>
  );
}
