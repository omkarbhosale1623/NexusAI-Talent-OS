"use client";

import { useState } from "react";
import { Users, CheckCircle2, AlertTriangle, Play } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScoreBadge } from "@/components/ui/score-badge";
import { EmptyState } from "@/components/ui/empty-state";

interface Props {
  interviewId: string;
}

type Variant = "success" | "warning" | "error" | "default";

function agreementVariant(agreement: any): Variant {
  if (typeof agreement === "string") {
    const a = agreement.toLowerCase();
    if (a.includes("high") || a.includes("strong")) return "success";
    if (a.includes("low") || a.includes("split") || a.includes("divid")) return "error";
    if (a.includes("med") || a.includes("mod")) return "warning";
    return "default";
  }
  const n = Number(agreement);
  if (isFinite(n)) {
    const pct = n <= 1 ? n * 100 : n;
    if (pct >= 75) return "success";
    if (pct >= 50) return "warning";
    return "error";
  }
  return "default";
}

function agreementLabel(agreement: any): string {
  if (typeof agreement === "string") return agreement;
  const n = Number(agreement);
  if (isFinite(n)) {
    const pct = n <= 1 ? n * 100 : n;
    return `${Math.round(pct)}% agreement`;
  }
  return "—";
}

export default function PanelResult({ interviewId }: Props) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const res: any = await api.panelEvaluate(interviewId);
      if (res?.ok === false) {
        setError(res?.reason ?? res?.message ?? "Panel evaluation failed.");
        setData(null);
      } else {
        setData(res);
      }
    } catch (e: any) {
      setError(e?.message ?? "Panel evaluation failed.");
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const personas: any[] = Array.isArray(data?.panel_scores) ? data.panel_scores : [];
  const consensusScore = Number(data?.consensus_score);

  return (
    <Card>
      <CardHeader>
        <CardTitle>AI Panel Evaluation</CardTitle>
        <CardDescription>
          Run a multi-persona panel to assess this candidate from diverse perspectives.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <div>
          <Button onClick={run} loading={loading} disabled={loading}>
            {!loading && <Play className="h-4 w-4" />}
            {data ? "Re-run Panel" : "Run Panel Evaluation"}
          </Button>
        </div>

        {error && (
          <div className="rounded-lg border border-error/30 bg-error-light p-3 text-sm text-error">
            {error}
          </div>
        )}

        {!data && !error && !loading && (
          <EmptyState
            icon={Users}
            title="No panel results yet"
            description="Run the panel evaluation to generate consensus scoring."
          />
        )}

        {data && (
          <>
            {/* Consensus */}
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-bg p-4">
              <div className="flex items-center gap-3">
                <span className="text-sm text-text-muted">Consensus Score</span>
                {isFinite(consensusScore) ? (
                  <ScoreBadge score={consensusScore} showMax size="lg" />
                ) : (
                  <span className="text-text-muted">—</span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={agreementVariant(data.agreement)}>
                  {agreementLabel(data.agreement)}
                </Badge>
                {data.consensus_recommendation && (
                  <Badge variant="outline">{String(data.consensus_recommendation)}</Badge>
                )}
              </div>
            </div>

            {data.summary && (
              <p className="text-sm text-text-primary">{data.summary}</p>
            )}

            {/* Persona cards */}
            <div className="grid gap-4 sm:grid-cols-2">
              {personas.map((p, i) => {
                const score = Number(p?.score);
                const strengths: any[] = Array.isArray(p?.strengths) ? p.strengths : [];
                const concerns: any[] = Array.isArray(p?.concerns) ? p.concerns : [];
                return (
                  <div key={i} className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-4">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-text-primary">
                        {p?.persona ?? `Persona ${i + 1}`}
                      </span>
                      {isFinite(score) && <ScoreBadge score={score} showMax />}
                    </div>
                    {p?.rating && (
                      <Badge variant="muted" className="self-start">
                        {String(p.rating)}
                      </Badge>
                    )}
                    {p?.notes && <p className="text-sm text-text-muted">{p.notes}</p>}

                    {strengths.length > 0 && (
                      <div className="flex flex-col gap-1">
                        <span className="text-xs font-medium uppercase tracking-wide text-success">
                          Strengths
                        </span>
                        <ul className="flex flex-col gap-1">
                          {strengths.map((s, si) => (
                            <li key={si} className="flex items-start gap-1.5 text-sm text-text-primary">
                              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />
                              <span>{typeof s === "string" ? s : JSON.stringify(s)}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {concerns.length > 0 && (
                      <div className="flex flex-col gap-1">
                        <span className="text-xs font-medium uppercase tracking-wide text-warning">
                          Concerns
                        </span>
                        <ul className="flex flex-col gap-1">
                          {concerns.map((c, ci) => (
                            <li key={ci} className="flex items-start gap-1.5 text-sm text-text-primary">
                              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" />
                              <span>{typeof c === "string" ? c : JSON.stringify(c)}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
