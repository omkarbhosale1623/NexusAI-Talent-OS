"use client";

import { useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/loading";
import { Progress } from "@/components/ui/progress";

interface Props {
  interviewId: string;
}

function num(v: any): number | null {
  const n = Number(v);
  return isFinite(n) ? n : null;
}

function CohortBar({
  candidate,
  cohort,
}: {
  candidate: number | null;
  cohort: any;
}) {
  const min = num(cohort?.p25);
  const max = num(cohort?.p75);
  const mean = num(cohort?.mean);
  const median = num(cohort?.median);

  // Build a scale that comfortably contains all points (0-100 default).
  const points = [candidate, min, max, mean, median].filter(
    (x): x is number => x != null
  );
  const lo = points.length ? Math.min(0, ...points) : 0;
  const hi = points.length ? Math.max(100, ...points) : 100;
  const span = hi - lo || 1;
  const pos = (v: number | null) =>
    v == null ? null : ((v - lo) / span) * 100;

  const boxLeft = pos(min);
  const boxRight = pos(max);
  const candPos = pos(candidate);
  const medPos = pos(median);

  return (
    <div className="flex flex-col gap-2">
      <div className="relative h-8 w-full rounded-full bg-border">
        {/* p25-p75 interquartile box */}
        {boxLeft != null && boxRight != null && (
          <div
            className="absolute top-0 h-full rounded-full bg-brand-light"
            style={{ left: `${boxLeft}%`, width: `${Math.max(0, boxRight - boxLeft)}%` }}
            title="P25–P75"
          />
        )}
        {/* median marker */}
        {medPos != null && (
          <div
            className="absolute top-0 h-full w-0.5 bg-text-muted"
            style={{ left: `${medPos}%` }}
            title="Median"
          />
        )}
        {/* candidate marker */}
        {candPos != null && (
          <div
            className="absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface bg-brand shadow"
            style={{ left: `${candPos}%` }}
            title="Candidate"
          />
        )}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-muted">
        <span>Mean: {mean != null ? mean.toFixed(1) : "—"}</span>
        <span>Median: {median != null ? median.toFixed(1) : "—"}</span>
        <span>P25: {min != null ? min.toFixed(1) : "—"}</span>
        <span>P75: {max != null ? max.toFixed(1) : "—"}</span>
        {num(cohort?.count) != null && <span>n = {cohort.count}</span>}
      </div>
    </div>
  );
}

export default function BenchmarkCard({ interviewId }: Props) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setData(null);
    setError(null);
    api
      .getBenchmark(interviewId)
      .then((res: any) => {
        if (!active) return;
        if (res?.ok === false) {
          setError(res?.reason ?? res?.message ?? "No benchmark data available.");
        } else {
          setData(res);
        }
      })
      .catch((e: any) => active && setError(e?.message ?? "Failed to load benchmark data."))
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
            icon={BarChart3}
            title="No benchmark data"
            description={error ?? undefined}
          />
        </CardContent>
      </Card>
    );
  }

  const candidateScore = num(data.candidate_score);
  const jobCohort = data.job_cohort ?? null;
  const orgCohort = data.org_cohort ?? null;
  const percentile = num(jobCohort?.percentile_rank);
  const competencies: Record<string, any> =
    data.competency_percentiles && typeof data.competency_percentiles === "object"
      ? data.competency_percentiles
      : {};
  const compEntries = Object.entries(competencies);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Benchmark vs Cohort</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        {/* Percentile rank */}
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
              Percentile Rank (Job Cohort)
            </p>
            <p className="mt-1 text-4xl font-bold tabular-nums text-brand">
              {percentile != null ? `${Math.round(percentile)}th` : "—"}
            </p>
          </div>
          {candidateScore != null && (
            <div className="text-right">
              <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
                Candidate Score
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-text-primary">
                {candidateScore.toFixed(1)}
              </p>
            </div>
          )}
        </div>

        {/* Job cohort bar */}
        {jobCohort && (
          <div className="flex flex-col gap-2">
            <span className="text-sm font-medium text-text-primary">Job Cohort</span>
            <CohortBar candidate={candidateScore} cohort={jobCohort} />
          </div>
        )}

        {/* Org cohort bar */}
        {orgCohort && (
          <div className="flex flex-col gap-2">
            <span className="text-sm font-medium text-text-primary">Org Cohort</span>
            <CohortBar candidate={candidateScore} cohort={orgCohort} />
          </div>
        )}

        {/* Competency percentiles */}
        {compEntries.length > 0 && (
          <div className="flex flex-col gap-3">
            <span className="text-sm font-medium text-text-primary">
              Competency Percentiles
            </span>
            {compEntries.map(([name, val]) => {
              const p = num(val);
              return (
                <div key={name} className="flex flex-col gap-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="capitalize text-text-primary">
                      {name.replace(/_/g, " ")}
                    </span>
                    <span className="tabular-nums text-text-muted">
                      {p != null ? `${Math.round(p)}th` : "—"}
                    </span>
                  </div>
                  <Progress value={p ?? 0} />
                </div>
              );
            })}
          </div>
        )}

        {/* Verdict */}
        {data.verdict && (
          <div className="rounded-lg border border-border bg-bg p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
              Verdict
            </p>
            <p className="mt-1 text-sm text-text-primary">{data.verdict}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
