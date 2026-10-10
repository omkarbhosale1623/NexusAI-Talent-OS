"use client";

import { useState, useEffect, use, useMemo } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Download,
  Share2,
  Calendar,
  CheckCircle2,
  AlertTriangle,
  Eye,
  MousePointerClick,
  ShieldCheck,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScoreBadge } from "@/components/ui/score-badge";
import { Progress } from "@/components/ui/progress";
import { cn, getRecommendationLabel, getScoreBg } from "@/lib/utils";
import type { Recommendation } from "@/types";
import { api } from "@/lib/api";

const REC_BADGE_STYLES: Record<string, string> = {
  strong_hire: "bg-success-light text-success border-success",
  hire: "bg-brand-light text-brand border-brand",
  maybe: "bg-warning-light text-warning border-warning",
  no_hire: "bg-error-light text-error border-error",
};

export default function ReportDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [report, setReport] = useState<any>(null);
  const [interview, setInterview] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api.getReport(id),
      api.getInterview(id)
    ])
    .then(([reportData, interviewData]) => {
      setReport(reportData);
      setInterview(interviewData);
    })
    .catch((err) => {
      console.error("Load report details error:", err);
      setError(err.message || "Failed to load report or interview details.");
    })
    .finally(() => setLoading(false));
  }, [id]);

  // Derived styling for recommendation
  const rec = useMemo(() => {
    if (!report?.evaluation?.recommendation) return null;
    const key = report.evaluation.recommendation.toLowerCase().replace(" ", "_");
    return {
      key,
      label: report.evaluation.recommendation,
      styleClass: REC_BADGE_STYLES[key] || "bg-brand-light text-brand border-brand"
    };
  }, [report]);

  // Map backend round_scores to UI rounds
  const rounds = useMemo(() => {
    if (!report?.evaluation) return [];
    const roundScores = report.evaluation.round_scores || {};
    const answerEvaluations = report.evaluation.answer_evaluations || [];
    
    const roundNames: Record<string, string> = {
      intro: "Introduction",
      technical: "Technical",
      behavioral: "Behavioral",
      hr: "HR & Culture fit",
    };

    return Object.keys(roundNames).map((rt, i) => {
      const score = roundScores[rt] || 0;
      const filteredAns = answerEvaluations.filter((ae: any) => ae.round_type === rt);
      
      const obs = filteredAns
        .map((ae: any) => ae.candidate_feedback)
        .filter(Boolean)
        .slice(0, 3);

      return {
        id: i + 1,
        name: roundNames[rt],
        score: Math.round(score),
        observations: obs.length > 0 ? obs : ["Good performance demonstrated in this round."],
      };
    });
  }, [report]);

  // Map backend competencies to skills list
  const skills = useMemo(() => {
    if (!report?.evaluation?.competency_scores) return [];
    return Object.entries(report.evaluation.competency_scores).map(([name, score]) => {
      const formattedName = name
        .replace(/_/g, " ")
        .split(" ")
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(" ");
      return {
        name: formattedName,
        score: Math.round(score as number),
      };
    });
  }, [report]);

  // Aggregate overall strengths
  const strengths = useMemo(() => {
    if (!report?.evaluation?.answer_evaluations) return [];
    const list = report.evaluation.answer_evaluations.flatMap((ae: any) => ae.strengths || []) as string[];
    return Array.from(new Set(list)).slice(0, 4) as string[];
  }, [report]);

  // Aggregate overall improvements
  const improvements = useMemo(() => {
    if (!report?.evaluation?.answer_evaluations) return [];
    const list = report.evaluation.answer_evaluations.flatMap((ae: any) => ae.improvements || []) as string[];
    return Array.from(new Set(list)).slice(0, 4) as string[];
  }, [report]);

  // Duration computation
  const durationMins = useMemo(() => {
    if (!interview?.started_at || !interview?.completed_at) return 45;
    const diffMs = new Date(interview.completed_at).getTime() - new Date(interview.started_at).getTime();
    return Math.max(1, Math.round(diffMs / 60000));
  }, [interview]);

  // Salary format
  const salaryRange = useMemo(() => {
    if (!report?.evaluation?.salary_recommendation) return null;
    const sal = report.evaluation.salary_recommendation;
    if (!sal.min || !sal.max) return null;
    return {
      min: sal.min,
      max: sal.max,
      currency: sal.currency === "INR" ? "₹" : sal.currency === "USD" ? "$" : sal.currency + " ",
      justification: sal.justification || "Recommended salary range based on overall assessment scores."
    };
  }, [report]);

  // Download plain-text report
  const handleDownloadText = async () => {
    if (!id || !report) return;
    try {
      const text = await api.getReportText(id);
      const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Interview_Report_${report.candidate?.full_name?.replace(/\s+/g, "_") || "Candidate"}.txt`;
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
        <p className="text-sm text-text-muted">Loading report details...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="max-w-md mx-auto text-center py-12">
        <AlertCircle className="h-12 w-12 text-error mx-auto mb-4" />
        <h1 className="text-xl font-bold text-text-primary mb-2">Error Loading Report</h1>
        <p className="text-sm text-text-muted mb-6">{error || "Failed to load report."}</p>
        <Button asChild size="sm">
          <Link href="/admin/reports">Back to Reports</Link>
        </Button>
      </div>
    );
  }

  const overallScore = Math.round(report.evaluation.overall_score || 0);

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-start gap-3">
        <Link
          href="/admin/reports"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-text-muted hover:bg-border hover:text-text-primary transition-colors duration-100 mt-1"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold text-text-primary">
            Assessment Report
          </h1>
          <p className="text-sm text-text-muted mt-0.5">
            {report.candidate?.full_name} · {report.job_title}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={handleDownloadText}>
            <Share2 className="h-4 w-4" />
            <span className="hidden sm:inline">Share TXT</span>
          </Button>
          <Button size="sm" onClick={handleDownloadText}>
            <Download className="h-4 w-4" />
            <span className="hidden sm:inline">Download TXT</span>
          </Button>
        </div>
      </div>

      {/* Score hero card */}
      <Card>
        <CardContent className="py-8">
          <div className="flex flex-col items-center gap-4 text-center">
            {/* Big score circle */}
            <div
              className={cn(
                "flex h-24 w-24 items-center justify-center rounded-full text-4xl font-black",
                getScoreBg(overallScore)
              )}
            >
              {overallScore}
            </div>
            <div>
              <p className="text-sm text-text-muted">Overall Score</p>
              <p className="text-xs text-text-muted mt-0.5 font-mono">
                <Calendar className="inline h-3 w-3 mr-1" />
                {interview.completed_at ? new Date(interview.completed_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "Completed"} · {durationMins} min
              </p>
            </div>
            {/* Recommendation */}
            {rec && (
              <span
                className={cn(
                  "rounded-full border px-5 py-1.5 text-sm font-bold",
                  rec.styleClass
                )}
              >
                {getRecommendationLabel(rec.key as Recommendation)}
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      <div>
        <h2 className="text-base font-semibold text-text-primary mb-3">
          Round Scores
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {rounds.map((round: any) => (
            <Card key={round.name} className="p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-text-primary">
                  {round.name}
                </h3>
                <ScoreBadge score={round.score} size="default" />
              </div>
              <ul className="space-y-1.5">
                {round.observations.map((obs: string, i: number) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-text-muted">
                    <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-text-muted" />
                    {obs}
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      </div>

      {/* Skill Assessment */}
      {skills.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Competency Assessment</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {skills.map((skill: any) => (
              <div key={skill.name}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm font-medium text-text-primary">
                    {skill.name}
                  </span>
                  <ScoreBadge score={skill.score} size="sm" />
                </div>
                <Progress value={skill.score} />
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Strengths + Improvements */}
      {(strengths.length > 0 || improvements.length > 0) && (
        <div className="grid gap-4 sm:grid-cols-2">
          {/* Strengths */}
          {strengths.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-success text-base font-semibold">
                  <CheckCircle2 className="h-4 w-4" />
                  Strengths
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {strengths.map((s: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-text-muted">
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-success mt-0.5" />
                      {s}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Areas for Improvement */}
          {improvements.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-warning text-base font-semibold">
                  <AlertTriangle className="h-4 w-4" />
                  Areas for Improvement
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {improvements.map((item: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-text-muted">
                      <AlertTriangle className="h-4 w-4 shrink-0 text-warning mt-0.5" />
                      {item}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Salary Recommendation */}
      {salaryRange && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Salary Recommendation</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-baseline gap-2 mb-2 font-mono">
              <span className="text-2xl font-bold text-text-primary">
                {salaryRange.currency}{Math.round(salaryRange.min).toLocaleString("en-US")}
              </span>
              <span className="text-text-muted">–</span>
              <span className="text-2xl font-bold text-text-primary">
                {salaryRange.currency}{Math.round(salaryRange.max).toLocaleString("en-US")}
              </span>
              <span className="text-sm text-text-muted">/ year</span>
            </div>
            <p className="text-sm text-text-muted leading-relaxed">
              {salaryRange.justification}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Proctoring Summary */}
      {report.proctoring_summary && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-semibold">
              <ShieldCheck className="h-4 w-4 text-success" />
              Proctoring Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-3 rounded-lg bg-bg">
                <Eye className="h-5 w-5 text-success mx-auto mb-1" />
                <p className="text-xl font-bold text-text-primary">
                  {report.proctoring_summary.integrity_score}%
                </p>
                <p className="text-xs text-text-muted mt-0.5">Attention Level</p>
              </div>
              <div className="text-center p-3 rounded-lg bg-bg">
                <MousePointerClick className="h-5 w-5 text-warning mx-auto mb-1" />
                <p className="text-xl font-bold text-text-primary">
                  {report.proctoring_summary.total_events}
                </p>
                <p className="text-xs text-text-muted mt-0.5">Violations</p>
              </div>
              <div className="text-center p-3 rounded-lg bg-bg">
                <ShieldCheck className="h-5 w-5 text-success mx-auto mb-1" />
                <p className="text-xl font-bold text-text-primary">
                  {report.proctoring_summary.integrity_score}%
                </p>
                <p className="text-xs text-text-muted mt-0.5">Integrity Score</p>
              </div>
            </div>
            <div className={cn(
              "mt-4 p-3 rounded-lg border",
              report.proctoring_summary.risk_level === "low"
                ? "bg-success-light border-success/20 text-success"
                : report.proctoring_summary.risk_level === "medium"
                ? "bg-warning-light border-warning/20 text-warning"
                : "bg-error-light border-error/20 text-error"
            )}>
              <p className="text-sm font-medium">
                {report.proctoring_summary.risk_level === "low"
                  ? "No significant integrity issues detected."
                  : `Integrity concerns detected. Risk classification: ${report.proctoring_summary.risk_level.toUpperCase()}.`}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="flex flex-wrap gap-3 pb-8">
        <Button size="sm" onClick={handleDownloadText}>
          <Download className="h-4 w-4" />
          Download TXT
        </Button>
        <Button variant="secondary" size="sm" onClick={handleDownloadText}>
          <Share2 className="h-4 w-4" />
          Share Report
        </Button>
        {interview?.candidate_id && (
          <Button asChild variant="ghost" size="sm">
            <Link href={`/admin/candidates/${interview.candidate_id}`}>
              View Candidate Profile
            </Link>
          </Button>
        )}
      </div>
    </div>
  );
}
