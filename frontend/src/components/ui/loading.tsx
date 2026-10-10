import * as React from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Spinner ──────────────────────────────────────────────────────────────────

export interface SpinnerProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: "sm" | "default" | "lg";
}

function Spinner({ size = "default", className, ...props }: SpinnerProps) {
  return (
    <div
      className={cn("flex items-center justify-center", className)}
      {...props}
    >
      <Loader2
        className={cn(
          "animate-spin text-brand",
          size === "sm" && "h-4 w-4",
          size === "default" && "h-6 w-6",
          size === "lg" && "h-8 w-8"
        )}
      />
    </div>
  );
}

// ─── Page Loading ─────────────────────────────────────────────────────────────

function PageLoading() {
  return (
    <div className="flex h-64 w-full items-center justify-center">
      <Spinner size="lg" />
    </div>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-border", className)}
      {...props}
    />
  );
}

// ─── Card Skeleton ────────────────────────────────────────────────────────────

function CardSkeleton() {
  return (
    <div className="bg-surface border border-border rounded-lg p-5 flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-full" />
        <div className="flex flex-col gap-2 flex-1">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-3 w-1/3" />
        </div>
      </div>
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-4/5" />
      <div className="flex gap-2 pt-1">
        <Skeleton className="h-6 w-16 rounded-full" />
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
    </div>
  );
}

// ─── Table Row Skeleton ───────────────────────────────────────────────────────

function TableRowSkeleton({ cols = 5 }: { cols?: number }) {
  return (
    <tr className="border-b border-border">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <Skeleton className="h-4 w-full max-w-[120px]" />
        </td>
      ))}
    </tr>
  );
}

// ─── Legacy alias (for backward compatibility) ────────────────────────────────

/** @deprecated Use Spinner instead */
function LoadingSpinner({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center justify-center py-16", className)}>
      <Loader2 className="h-6 w-6 animate-spin text-brand" />
    </div>
  );
}

export { Spinner, PageLoading, Skeleton, CardSkeleton, TableRowSkeleton, LoadingSpinner };
