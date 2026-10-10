"use client";

import { useEffect, useState } from "react";
import { ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/loading";

interface Props {
  interviewId: string;
}

type Variant = "success" | "warning" | "error" | "default";

function levelVariant(level?: string, score?: number): Variant {
  const l = (level ?? "").toLowerCase();
  if (l.includes("high")) return "error";
  if (l.includes("med")) return "warning";
  if (l.includes("low")) return "success";
  // Fallback on score (0-100)
  if (typeof score === "number") {
    if (score >= 67) return "error";
    if (score >= 34) return "warning";
    return "success";
  }
  return "default";
}

const gaugeBg: Record<Variant, string> = {
  success: "bg-success",
  warning: "bg-warning",
  error: "bg-error",
  default: "bg-brand",
};

export default function FraudPanel({ interviewId }: Props) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setData(null);
    setError(null);
    api
      .getFraudSummary(interviewId)
      .then((res: any) => {
        if (!active) return;
        if (res?.ok === false) {
          setError(res?.reason ?? res?.message ?? "No integrity data available.");
        } else {
          setData(res);
        }
      })
      .catch((e: any) => active && setError(e?.message ?? "Failed to load integrity data."))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [interviewId]);

  if (loading) {
    return (
      <Card>
        <CardContent>
          <Spinner className="py-10" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardContent>
          <EmptyState
            icon={ShieldAlert}
            title="No integrity data"
            description={error ?? undefined}
          />
        </CardContent>
      </Card>
    );
  }

  const rawScore = Number(data.fraud_risk_score ?? 0);
  const score = Math.min(100, Math.max(0, Math.round(rawScore)));
  const level = data.risk_level ?? "unknown";
  const variant = levelVariant(level, score);
  const flags: any[] = Array.isArray(data.flags) ? data.flags : [];
  const counts: Record<string, number> = data.counts && typeof data.counts === "object" ? data.counts : {};
  const countEntries = Object.entries(counts);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Integrity &amp; Fraud Detection</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        {/* Risk gauge */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-text-muted">Fraud Risk Score</span>
            <Badge variant={variant}>{String(level).toUpperCase()}</Badge>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative h-3 w-full overflow-hidden rounded-full bg-border">
              <div
                className={cn("h-full rounded-full transition-all duration-500", gaugeBg[variant])}
                style={{ width: `${score}%` }}
              />
            </div>
            <span className="w-12 shrink-0 text-right text-sm font-semibold tabular-nums text-text-primary">
              {score}
            </span>
          </div>
        </div>

        {/* Flags */}
        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium text-text-primary">Flags</span>
          {flags.length === 0 ? (
            <p className="text-sm text-text-muted">No flags raised.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {flags.map((f, i) => (
                <Badge key={i} variant="warning">
                  {typeof f === "string" ? f : f?.label ?? f?.type ?? f?.message ?? "flag"}
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* Event counts table */}
        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium text-text-primary">Event Counts</span>
          {countEntries.length === 0 ? (
            <p className="text-sm text-text-muted">No events recorded.</p>
          ) : (
            <div className="overflow-hidden rounded-lg border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-bg">
                    <th className="px-4 py-2 text-left font-medium text-text-muted">Event Type</th>
                    <th className="px-4 py-2 text-right font-medium text-text-muted">Count</th>
                  </tr>
                </thead>
                <tbody>
                  {countEntries.map(([type, n]) => (
                    <tr key={type} className="border-b border-border last:border-0">
                      <td className="px-4 py-2 text-text-primary">{type}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-text-primary">{n}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Recommendation */}
        {data.recommendation && (
          <div className="rounded-lg border border-border bg-bg p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-text-muted">Recommendation</p>
            <p className="mt-1 text-sm text-text-primary">{data.recommendation}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
