"use client";

import { useEffect, useState } from "react";
import { Brain, Search } from "lucide-react";
import AdminLayout from "@/components/layout/admin-layout";
import { api } from "@/lib/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { EmptyState } from "@/components/ui/empty-state";

import VideoPlayback from "@/components/evaluation/VideoPlayback";
import FraudPanel from "@/components/evaluation/FraudPanel";
import ProsodyTimeline from "@/components/evaluation/ProsodyTimeline";
import BenchmarkCard from "@/components/evaluation/BenchmarkCard";
import PanelResult from "@/components/evaluation/PanelResult";
import RecruiterFeedbackForm from "@/components/evaluation/RecruiterFeedbackForm";

function pct(v: any): string {
  const n = Number(v);
  if (!isFinite(n)) return "—";
  const p = n <= 1 ? n * 100 : n;
  return `${Math.round(p)}%`;
}

function CalibrationCard() {
  const [stats, setStats] = useState<any>(null);
  const [calibration, setCalibration] = useState<any>(null);
  const [whStatus, setWhStatus] = useState<any>(null);
  const [whMetrics, setWhMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      api.getLearningStats(),
      api.getCalibration(),
      api.warehouseStatus(),
      api.warehouseMetrics("avg_score_by_job"),
    ]).then((results) => {
      if (!active) return;
      const val = (r: PromiseSettledResult<any>) =>
        r.status === "fulfilled" && r.value?.ok !== false ? r.value : null;
      setStats(val(results[0]));
      setCalibration(val(results[1]));
      setWhStatus(val(results[2]));
      setWhMetrics(val(results[3]));
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  // Defensive extraction of metric rows.
  const metricRows: any[] = Array.isArray(whMetrics)
    ? whMetrics
    : Array.isArray(whMetrics?.rows)
    ? whMetrics.rows
    : Array.isArray(whMetrics?.data)
    ? whMetrics.data
    : [];

  const calibrationHints: any[] = Array.isArray(calibration?.hints)
    ? calibration.hints
    : Array.isArray(calibration)
    ? calibration
    : [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Model Calibration &amp; Analytics</CardTitle>
        <CardDescription>
          Continuous learning health and warehouse metrics.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        {loading ? (
          <p className="text-sm text-text-muted">Loading analytics…</p>
        ) : (
          <>
            {/* Learning stats */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div className="rounded-lg border border-border bg-bg p-4">
                <p className="text-xs uppercase tracking-wide text-text-muted">
                  Agreement Rate
                </p>
                <p className="mt-1 text-xl font-semibold text-text-primary">
                  {pct(stats?.agreement_rate)}
                </p>
              </div>
              <div className="rounded-lg border border-border bg-bg p-4">
                <p className="text-xs uppercase tracking-wide text-text-muted">
                  Feedback Count
                </p>
                <p className="mt-1 text-xl font-semibold text-text-primary">
                  {stats?.feedback_count ?? stats?.total_feedback ?? "—"}
                </p>
              </div>
              <div className="rounded-lg border border-border bg-bg p-4">
                <p className="text-xs uppercase tracking-wide text-text-muted">
                  Warehouse
                </p>
                <p className="mt-1 text-xl font-semibold text-text-primary capitalize">
                  {whStatus?.status ?? (whStatus ? "ok" : "—")}
                </p>
              </div>
              <div className="rounded-lg border border-border bg-bg p-4">
                <p className="text-xs uppercase tracking-wide text-text-muted">
                  Rows Synced
                </p>
                <p className="mt-1 text-xl font-semibold text-text-primary">
                  {whStatus?.row_count ?? whStatus?.rows ?? "—"}
                </p>
              </div>
            </div>

            {/* Calibration hints */}
            {calibrationHints.length > 0 && (
              <div className="flex flex-col gap-2">
                <span className="text-sm font-medium text-text-primary">
                  Calibration Hints
                </span>
                <div className="flex flex-wrap gap-2">
                  {calibrationHints.map((h, i) => (
                    <Badge key={i} variant="outline">
                      {typeof h === "string" ? h : h?.label ?? h?.message ?? JSON.stringify(h)}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Warehouse metrics */}
            <div className="flex flex-col gap-2">
              <span className="text-sm font-medium text-text-primary">
                Avg Score by Job
              </span>
              {metricRows.length === 0 ? (
                <p className="text-sm text-text-muted">No metrics available.</p>
              ) : (
                <div className="overflow-x-auto rounded-lg border border-border">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-bg">
                        {Object.keys(metricRows[0] ?? {}).map((col) => (
                          <th
                            key={col}
                            className="px-4 py-2 text-left font-medium text-text-muted"
                          >
                            {col.replace(/_/g, " ")}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {metricRows.map((row, i) => (
                        <tr key={i} className="border-b border-border last:border-0">
                          {Object.values(row).map((v: any, j) => (
                            <td key={j} className="px-4 py-2 text-text-primary">
                              {typeof v === "number" ? v.toLocaleString() : String(v ?? "—")}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function IntelligencePage() {
  const [inputId, setInputId] = useState("");
  const [interviewId, setInterviewId] = useState<string | null>(null);

  const load = () => {
    const id = inputId.trim();
    if (id) setInterviewId(id);
  };

  return (
    <AdminLayout title="Interview Intelligence">
      <div className="flex flex-col gap-6">
        {/* Interview loader */}
        <Card>
          <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <Input
                label="Interview ID"
                value={inputId}
                onChange={(e) => setInputId(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && load()}
                placeholder="Enter an interview ID to analyze"
              />
            </div>
            <Button onClick={load} disabled={!inputId.trim()}>
              <Search className="h-4 w-4" />
              Load
            </Button>
          </CardContent>
        </Card>

        {interviewId ? (
          <Tabs defaultValue="recording">
            <TabsList className="flex-wrap">
              <TabsTrigger value="recording">Recording</TabsTrigger>
              <TabsTrigger value="integrity">Integrity</TabsTrigger>
              <TabsTrigger value="prosody">Prosody</TabsTrigger>
              <TabsTrigger value="benchmark">Benchmark</TabsTrigger>
              <TabsTrigger value="panel">Panel</TabsTrigger>
              <TabsTrigger value="feedback">Feedback</TabsTrigger>
            </TabsList>

            <TabsContent value="recording">
              <VideoPlayback interviewId={interviewId} />
            </TabsContent>
            <TabsContent value="integrity">
              <FraudPanel interviewId={interviewId} />
            </TabsContent>
            <TabsContent value="prosody">
              <ProsodyTimeline interviewId={interviewId} />
            </TabsContent>
            <TabsContent value="benchmark">
              <BenchmarkCard interviewId={interviewId} />
            </TabsContent>
            <TabsContent value="panel">
              <PanelResult interviewId={interviewId} />
            </TabsContent>
            <TabsContent value="feedback">
              <RecruiterFeedbackForm interviewId={interviewId} />
            </TabsContent>
          </Tabs>
        ) : (
          <Card>
            <CardContent>
              <EmptyState
                icon={Brain}
                title="No interview loaded"
                description="Enter an interview ID above and click Load to view intelligence."
              />
            </CardContent>
          </Card>
        )}

        {/* Calibration & analytics */}
        <CalibrationCard />
      </div>
    </AdminLayout>
  );
}
