"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { Download, FileText, ArrowUpDown, AlertCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar } from "@/components/ui/avatar";
import { ScoreBadge } from "@/components/ui/score-badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { cn, formatDate, getRecommendationLabel } from "@/lib/utils";
import type { Recommendation } from "@/types";
import { api } from "@/lib/api";

interface ReportItem {
  id: string; // interview ID
  candidate: string;
  job: string;
  score: number;
  recommendation: Recommendation;
  date: string;
}

const REC_FILTERS: { key: Recommendation | "all"; label: string }[] = [
  { key: "all", label: "All" },
  { key: "strong_hire", label: "Strong Hire" },
  { key: "hire", label: "Hire" },
  { key: "maybe", label: "Maybe" },
  { key: "no_hire", label: "No Hire" },
];

const REC_BADGE_STYLES: Record<Recommendation, string> = {
  strong_hire: "bg-success-light text-success",
  hire: "bg-brand-light text-brand",
  maybe: "bg-warning-light text-warning",
  no_hire: "bg-error-light text-error",
};

type SortField = "date" | "score";

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [recFilter, setRecFilter] = useState<Recommendation | "all">("all");
  const [sort, setSort] = useState<SortField>("date");
  const [sortAsc, setSortAsc] = useState(false);

  useEffect(() => {
    async function loadReports() {
      try {
        // Step 1: List all interviews
        const interviewsRes = await api.listInterviews({ page: 1, page_size: 100 });
        const interviewList = interviewsRes.items || [];

        // Step 2: Filter completed or evaluated ones and fetch their report info
        const evaluatedInterviews = interviewList.filter(
          (iv: any) => iv.status === "evaluated" || iv.status === "completed"
        );

        const reportsData = await Promise.all(
          evaluatedInterviews.map(async (iv: any) => {
            try {
              const rep = await api.getReport(iv.id);
              const recKey = (rep.evaluation?.recommendation || "maybe")
                .toLowerCase()
                .replace(" ", "_") as Recommendation;

              return {
                id: iv.id,
                candidate: rep.candidate?.full_name || "Unknown Candidate",
                job: rep.job_title || "Unknown Job",
                score: Math.round(rep.evaluation?.overall_score || 0),
                recommendation: recKey,
                date: iv.completed_at || iv.created_at || new Date().toISOString(),
              };
            } catch (err) {
              console.error(`Failed to fetch report for interview ${iv.id}:`, err);
              return null;
            }
          })
        );

        setReports(reportsData.filter((r): r is ReportItem => r !== null));
      } catch (err: any) {
        console.error("Load reports error:", err);
        setError("Failed to load evaluation reports.");
      } finally {
        setLoading(false);
      }
    }

    loadReports();
  }, []);

  const toggleSort = (field: SortField) => {
    if (sort === field) {
      setSortAsc((v) => !v);
    } else {
      setSort(field);
      setSortAsc(false);
    }
  };

  const filtered = useMemo(() => {
    return reports
      .filter((r) => recFilter === "all" || r.recommendation === recFilter)
      .sort((a, b) => {
        let val = 0;
        if (sort === "date") {
          val = new Date(a.date).getTime() - new Date(b.date).getTime();
        } else {
          val = a.score - b.score;
        }
        return sortAsc ? val : -val;
      });
  }, [reports, recFilter, sort, sortAsc]);

  const handleDownloadText = async (interviewId: string, candidateName: string) => {
    try {
      const text = await api.getReportText(interviewId);
      const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Interview_Report_${candidateName.replace(/\s+/g, "_")}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download error:", err);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[300px]">
        <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-sm text-text-muted">Loading evaluation reports...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-md mx-auto text-center py-12">
        <AlertCircle className="h-12 w-12 text-error mx-auto mb-4" />
        <h1 className="text-xl font-bold text-text-primary mb-2">Error Loading Reports</h1>
        <p className="text-sm text-text-muted mb-6">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Assessment Reports</h1>
        <p className="text-sm text-text-muted mt-0.5">
          {reports.length} completed interview reports.
        </p>
      </div>

      {/* Filters + sort */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Recommendation filter */}
        <div className="flex flex-wrap gap-2">
          {REC_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setRecFilter(f.key)}
              className={cn(
                "px-3 py-1.5 rounded-full text-sm font-medium transition-colors duration-100",
                recFilter === f.key
                  ? "bg-brand text-white"
                  : "bg-border text-text-muted hover:text-text-primary"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Sort buttons */}
        <div className="ml-auto flex gap-2">
          {(["date", "score"] as SortField[]).map((field) => (
            <button
              key={field}
              onClick={() => toggleSort(field)}
              className={cn(
                "flex items-center gap-1 px-3 py-1.5 rounded-lg border text-sm font-medium transition-colors duration-100",
                sort === field
                  ? "border-brand text-brand bg-brand-light"
                  : "border-border text-text-muted hover:border-brand/40"
              )}
            >
              <ArrowUpDown className="h-3.5 w-3.5" />
              {field.charAt(0).toUpperCase() + field.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Reports grid */}
      {filtered.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No reports found"
          description="No reports match the selected filter."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {filtered.map((r) => (
            <Card key={r.id} className="p-5">
              {/* Candidate info */}
              <div className="flex items-center gap-3">
                <Avatar size="default" name={r.candidate} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-text-primary truncate">
                    {r.candidate}
                  </p>
                  <p className="text-xs text-text-muted truncate">{r.job}</p>
                </div>
              </div>

              {/* Score + recommendation */}
              <div className="flex items-center justify-between mt-4">
                <div className="flex items-center gap-3">
                  <ScoreBadge score={r.score} size="lg" />
                  <div>
                    <p className="text-xs text-text-muted">Overall</p>
                    <p className="text-sm font-semibold text-text-primary">
                      {r.score}/100
                    </p>
                  </div>
                </div>
                <span
                  className={cn(
                    "rounded-full px-3 py-1 text-xs font-semibold border",
                    REC_BADGE_STYLES[r.recommendation] || "bg-brand-light text-brand"
                  )}
                >
                  {getRecommendationLabel(r.recommendation)}
                </span>
              </div>

              <p className="text-xs text-text-muted mt-3 font-mono">
                {formatDate(r.date)}
              </p>

              {/* Actions */}
              <div className="flex items-center gap-2 mt-4 pt-4 border-t border-border">
                <Button asChild size="sm" className="flex-1">
                  <Link href={`/admin/reports/${r.id}`}>View Report</Link>
                </Button>
                <Button variant="secondary" size="sm" onClick={() => handleDownloadText(r.id, r.candidate)}>
                  <Download className="h-4 w-4" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
