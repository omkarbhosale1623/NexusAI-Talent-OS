"use client";

import { useEffect, useState } from "react";
import { AudioLines } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/loading";

interface Props {
  interviewId: string;
}

// Confidence values may be 0-1 or 0-100; normalize to 0-100.
function toPct(v: any): number {
  const n = Number(v);
  if (!isFinite(n)) return 0;
  const pct = n <= 1 ? n * 100 : n;
  return Math.min(100, Math.max(0, Math.round(pct)));
}

export default function ProsodyTimeline({ interviewId }: Props) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setData(null);
    setError(null);
    api
      .getProsody(interviewId)
      .then((res: any) => {
        if (!active) return;
        if (res?.ok === false) {
          setError(res?.reason ?? res?.message ?? "No prosody data available.");
        } else {
          setData(res);
        }
      })
      .catch((e: any) => active && setError(e?.message ?? "Failed to load prosody data."))
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

  const answers: any[] = Array.isArray(data?.answers) ? data.answers : [];

  if (error || (!data?.aggregate && answers.length === 0)) {
    return (
      <Card>
        <CardContent>
          <EmptyState
            icon={AudioLines}
            title="No prosody data"
            description={error ?? undefined}
          />
        </CardContent>
      </Card>
    );
  }

  const aggregate = data?.aggregate ?? {};
  const aggConfidence = toPct(aggregate?.confidence);
  const aggEmotion = aggregate?.emotion ?? "—";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Prosody &amp; Emotion</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        {/* Aggregate summary */}
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-lg border border-border bg-bg p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
              Overall Confidence
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-text-primary">
              {aggConfidence}%
            </p>
          </div>
          <div className="rounded-lg border border-border bg-bg p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
              Dominant Emotion
            </p>
            <p className="mt-1 text-2xl font-semibold capitalize text-text-primary">
              {String(aggEmotion)}
            </p>
          </div>
        </div>

        {/* Per-answer timeline */}
        <div className="flex flex-col gap-4">
          <span className="text-sm font-medium text-text-primary">Per-Answer Breakdown</span>
          {answers.length === 0 ? (
            <p className="text-sm text-text-muted">No per-answer prosody available.</p>
          ) : (
            answers.map((a, i) => {
              const prosody = a?.prosody ?? {};
              const conf = toPct(prosody?.confidence);
              const emotion = prosody?.emotion ?? "—";
              const q = a?.question_text ?? `Answer ${i + 1}`;
              return (
                <div key={i} className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between gap-3">
                    <span className="truncate text-sm text-text-primary" title={q}>
                      {i + 1}. {q}
                    </span>
                    <Badge variant="outline" className="shrink-0 capitalize">
                      {String(emotion)}
                    </Badge>
                  </div>
                  <Progress value={conf} showLabel />
                </div>
              );
            })
          )}
        </div>
      </CardContent>
    </Card>
  );
}
