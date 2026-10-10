"use client";

import { useState, useEffect, use, useMemo } from "react";
import Link from "next/link";
import {
  Download,
  ArrowLeft,
  CheckCircle2,
  TrendingUp,
  Star,
  Info,
  ChevronRight,
  AlertCircle,
  Lock,
} from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScoreBadge } from "@/components/ui/score-badge";
import { Progress } from "@/components/ui/progress";
import { cn, getScoreColor } from "@/lib/utils";
import { api } from "@/lib/api";

const RECOMMENDATION_STYLE: Record<string, { label: string; className: string }> = {
  strong_hire: { label: "Strong Hire", className: "bg-success-light text-success" },
  hire: { label: "Hire", className: "bg-brand-light text-brand" },
  maybe: { label: "Maybe", className: "bg-warning-light text-warning" },
  no_hire: { label: "No Hire", className: "bg-error-light text-error" },
};

function ScoreCircle({ score }: { score: number }) {
  const circumference = 2 * Math.PI * 40;
  const strokeDash = (score / 100) * circumference;

  const colorClass =
    score >= 85
      ? "text-success stroke-success"
      : score >= 70
      ? "text-brand stroke-brand"
      : score >= 55
      ? "text-warning stroke-warning"
      : "text-error stroke-error";

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg className="h-28 w-28 -rotate-90" viewBox="0 0 100 100">
        <circle
          cx="50"
          cy="50"
          r="40"
          fill="none"
          className="stroke-border"
          strokeWidth="8"
        />
        <circle
          cx="50"
          cy="50"
          r="40"
          fill="none"
          className={cn("transition-all duration-700", colorClass)}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${strokeDash} ${circumference}`}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className={cn("text-3xl font-bold tabular-nums", colorClass.split(" ")[0])}>
          {Math.round(score)}
        </span>
        <span className="text-xs text-text-muted">/100</span>
      </div>
    </div>
  );
}

export default function CandidateReportPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const [portal, setPortal] = useState<any>(null);
  const [interview, setInterview] = useState<any>(null);
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadData() {
      try {
        // Step 1: Get Candidate Portal info to verify visibility
        const portalData = await api.getCandidatePortal(token);
        if (!active) return;
        setPortal(portalData);

        if (!portalData.can_view_report) {
          setLoading(false);
          return;
        }

        // Step 2: Get Interview to find interview UUID
        const iv = await api.getInterviewByToken(token);
        if (!active) return;
        setInterview(iv);

        // Step 3: Get Report by interview ID
        const reportData = await api.getReport(iv.id);
        if (!active) return;
        setReport(reportData);
      } catch (err: any) {
        console.error("Load report error:", err);
        if (active) setError(err.message || "Failed to load evaluation report.");
      } finally {
        if (active) setLoading(false);
      }
    }

    loadData();

    return () => {
      active = false;
    };
  }, [token]);

  // Derived styling for recommendation
  const rec = useMemo(() => {
    if (!report?.evaluation?.recommendation) return null;
    const key = report.evaluation.recommendation.toLowerCase().replace(" ", "_");
    return RECOMMENDATION_STYLE[key] || {
      label: report.evaluation.recommendation,
      className: "bg-brand-light text-brand",
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
      hr: "HR & Culture",
    };

    return Object.keys(roundNames).map((rt, i) => {
      const score = roundScores[rt] || 0;
      const filteredAns = answerEvaluations.filter((ae: any) => ae.round_type === rt);
      
      const obs = filteredAns
        .map((ae: any) => ae.candidate_feedback)
        .filter(Boolean)
        .slice(0, 3);
        
      const strengths = Array.from(
        new Set(filteredAns.flatMap((ae: any) => ae.strengths || []))
      ).slice(0, 3);

      return {
        id: i + 1,
        name: roundNames[rt],
        score: Math.round(score),
        observations: obs.length > 0 ? obs : ["Good performance demonstrated in this round."],
        strengths: strengths.length > 0 ? strengths : ["Competency demonstrated"],
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

  // Generate salary recommendation text
  const salaryRecommendation = useMemo(() => {
    if (!report?.evaluation?.salary_recommendation) return "N/A";
    const sal = report.evaluation.salary_recommendation;
    if (!sal.min || !sal.max) return "N/A";
    const currencySym = sal.currency === "USD" ? "$" : sal.currency + " ";
    return `${currencySym}${Math.round(sal.min / 1000)}K – ${currencySym}${Math.round(sal.max / 1000)}K`;
  }, [report]);

  // Download plain-text report
  const handleDownloadText = async () => {
    if (!interview?.id || !report) return;
    try {
      const text = await api.getReportText(interview.id);
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
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-sm text-text-muted">Loading evaluation report...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-md mx-auto text-center py-12">
        <AlertCircle className="h-12 w-12 text-error mx-auto mb-4" />
        <h1 className="text-xl font-bold text-text-primary mb-2">Error Loading Report</h1>
        <p className="text-sm text-text-muted mb-6">{error}</p>
        <Button asChild size="sm">
          <Link href="/portal">Back to Portal</Link>
        </Button>
      </div>
    );
  }

  // Render "Under Review" state if not allowed to view yet
  if (portal && !portal.can_view_report) {
    return (
      <div className="max-w-md mx-auto text-center py-16">
        <div className="h-16 w-16 bg-brand-light flex items-center justify-center rounded-full mx-auto mb-6 text-brand">
          <Lock className="h-8 w-8" />
        </div>
        <h1 className="text-2xl font-bold text-text-primary mb-3">Assessment Under Review</h1>
        <p className="text-sm text-text-muted leading-relaxed mb-8">
          Thank you for completing your interview. Your assessment report is currently being reviewed
          by the hiring team. You will be notified when your feedback is available.
        </p>
        <Button asChild size="sm">
          <Link href={`/portal?token=${token}`}>Return to Portal</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Back nav */}
      <div className="flex items-center justify-between mb-6">
        <Link
          href={`/portal?token=${token}`}
          className="inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-text-primary transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Portal
        </Link>
        <Button variant="secondary" size="sm" onClick={handleDownloadText}>
          <Download className="h-3.5 w-3.5" />
          Download TXT
        </Button>
      </div>

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary">
          Your Interview Assessment
        </h1>
        <p className="text-sm text-text-muted mt-1 font-medium">
          {report.job_title} · {portal?.company_name || "NexusAI"} · {interview.completed_at ? new Date(interview.completed_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "Completed"}
        </p>
      </div>

      {/* Overall score card */}
      <Card className="mb-5">
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row items-center gap-6">
            <ScoreCircle score={report.evaluation.overall_score} />
            <div className="flex-1 text-center sm:text-left">
              <h2 className="text-xl font-bold text-text-primary mb-2">
                Overall Score
              </h2>
              {rec && (
                <div className="flex items-center gap-2 justify-center sm:justify-start mb-3">
                  <span
                    className={cn(
                      "inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold",
                      rec.className
                    )}
                  >
                    {rec.label}
                  </span>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-text-muted text-xs">Duration</p>
                  <p className="font-semibold text-text-primary">
                    {interview.started_at && interview.completed_at
                      ? `${Math.max(1, Math.round((new Date(interview.completed_at).getTime() - new Date(interview.started_at).getTime()) / 60000))} min`
                      : "N/A"}
                  </p>
                </div>
                <div>
                  <p className="text-text-muted text-xs">Integrity Score</p>
                  <p className="font-semibold text-success">
                    {report.proctoring_summary?.integrity_score || 100}%
                  </p>
                </div>
                {report.evaluation.salary_recommendation && (
                  <div>
                    <p className="text-text-muted text-xs">Salary Guidance</p>
                    <p className="font-semibold text-text-primary">{salaryRecommendation}</p>
                  </div>
                )}
                <div>
                  <p className="text-text-muted text-xs">Rounds Completed</p>
                  <p className="font-semibold text-text-primary">
                    {rounds.filter(r => r.score > 0).length} / {rounds.length}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Per-round breakdown */}
      <div className="mb-5">
        <h2 className="text-base font-semibold text-text-primary mb-3">
          Round Breakdown
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {rounds.map((round: any) => (
            <Card key={round.id}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div>
                    <p className="text-xs text-text-muted font-mono">Round {round.id}</p>
                    <h3 className="text-sm font-semibold text-text-primary">
                      {round.name}
                    </h3>
                  </div>
                  <ScoreBadge score={round.score} size="sm" />
                </div>

                <ul className="space-y-1.5 mb-3">
                  {round.observations.map((obs: string, i: number) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs text-text-muted">
                      <ChevronRight className="h-3 w-3 text-brand shrink-0 mt-0.5" />
                      {obs}
                    </li>
                  ))}
                </ul>

                <div className="flex flex-wrap gap-1">
                  {round.strengths.map((s: string) => (
                    <span
                      key={s}
                      className="text-[10px] font-medium bg-brand-light text-brand px-2 py-0.5 rounded-full"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Skill assessment bars */}
      {skills.length > 0 && (
        <Card className="mb-5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="h-4 w-4 text-brand" />
              Competency Assessment
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-3">
            <div className="space-y-4">
              {skills.map((skill: any) => (
                <div key={skill.name}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm text-text-primary font-medium">
                      {skill.name}
                    </span>
                    <span
                      className={cn(
                        "text-sm font-semibold tabular-nums",
                        getScoreColor(skill.score)
                      )}
                    >
                      {skill.score}
                    </span>
                  </div>
                  <Progress value={skill.score} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Strengths + Improvements */}
      {(strengths.length > 0 || improvements.length > 0) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
          {/* Strengths */}
          {strengths.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-success text-base">
                  <CheckCircle2 className="h-4 w-4" />
                  Key Strengths
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-3">
                <ul className="space-y-2.5">
                  {strengths.map((s: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-text-muted">
                      <div className="h-5 w-5 rounded-full bg-success-light flex items-center justify-center shrink-0 mt-0.5">
                        <CheckCircle2 className="h-3 w-3 text-success" />
                      </div>
                      {s}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Areas for improvement */}
          {improvements.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-warning text-base">
                  <Star className="h-4 w-4" />
                  Growth Opportunities
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-3">
                <ul className="space-y-2.5">
                  {improvements.map((item: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-text-muted">
                      <div className="h-5 w-5 rounded-full bg-warning-light flex items-center justify-center shrink-0 mt-0.5">
                        <TrendingUp className="h-3 w-3 text-warning" />
                      </div>
                      {item}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Disclaimer */}
      <div className="flex items-start gap-2.5 p-4 rounded-lg bg-bg border border-border mb-6">
        <Info className="h-4 w-4 text-text-muted shrink-0 mt-0.5" />
        <p className="text-xs text-text-muted leading-relaxed">
          This report was generated by NexusAI Talent OS AI based on your interview
          responses. The hiring team will make the final hiring decision. Assessment
          scores reflect performance during this interview session.
        </p>
      </div>

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-3">
        <Button variant="secondary" className="gap-2 flex-1" onClick={handleDownloadText}>
          <Download className="h-4 w-4" />
          Download TXT Report
        </Button>
        <Button asChild className="flex-1">
          <Link href={`/portal?token=${token}`}>Back to Portal</Link>
        </Button>
      </div>
    </div>
  );
}
