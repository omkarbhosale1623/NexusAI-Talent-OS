"use client";

import { useState, useEffect, use, useMemo } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  Clock,
  MessageSquare,
  Layers,
  Shield,
  FileText,
  Mail,
  Users,
  ArrowLeft,
  AlertCircle,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

const NEXT_STEPS = [
  {
    icon: FileText,
    title: "Report being generated",
    description: "Your assessment report will be ready within 2 minutes",
    color: "text-brand bg-brand-light",
  },
  {
    icon: Mail,
    title: "Email notification",
    description: "You'll receive an email when your report is available",
    color: "text-warning bg-warning-light",
  },
  {
    icon: Users,
    title: "Hiring team review",
    description: "The hiring team will review your assessment and be in touch",
    color: "text-success bg-success-light",
  },
];

export default function InterviewDonePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const [interview, setInterview] = useState<any>(null);
  const [reportReady, setReportReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    api.getInterviewByToken(token)
      .then(async (iv) => {
        if (!active) return;
        setInterview(iv);
        setLoading(false);

        // Try to trigger evaluation (safe/idempotent post)
        try {
          await api.triggerEvaluation(iv.id);
        } catch (e) {
          console.warn("Evaluation trigger notice:", e);
        }

        // Poll for evaluation
        try {
          await api.pollEvaluation(iv.id);
          if (active) setReportReady(true);
        } catch (err: any) {
          console.error("Polling evaluation error:", err);
          if (active) setError("Report generation took longer than expected.");
        }
      })
      .catch((err) => {
        console.error("Load interview error:", err);
        if (active) {
          setError("Failed to load interview details.");
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [token]);

  const stats = useMemo(() => {
    if (!interview) return [];
    
    // Calculate duration
    let durationStr = "45 minutes";
    if (interview.started_at && interview.completed_at) {
      const diffMs = new Date(interview.completed_at).getTime() - new Date(interview.started_at).getTime();
      const mins = Math.max(1, Math.round(diffMs / 60000));
      durationStr = `${mins} minutes`;
    }

    const qCount = String(interview.current_question_index || interview.total_questions || 0);
    const integrity = Math.round((1 - (interview.proctoring_risk_score || 0)) * 100);

    return [
      { icon: Clock, label: "Duration", value: durationStr, color: "text-brand" },
      { icon: MessageSquare, label: "Questions Answered", value: qCount, color: "text-brand" },
      { icon: Layers, label: "Rounds Completed", value: "4 / 4", color: "text-success" },
      { icon: Shield, label: "Integrity Score", value: `${integrity}%`, color: "text-success" },
    ];
  }, [interview]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-sm text-text-muted">Loading interview status...</p>
      </div>
    );
  }

  if (error && !interview) {
    return (
      <div className="max-w-md mx-auto text-center py-12">
        <AlertCircle className="h-12 w-12 text-error mx-auto mb-4" />
        <h1 className="text-xl font-bold text-text-primary mb-2">Error loading interview</h1>
        <p className="text-sm text-text-muted mb-6">{error}</p>
        <Button asChild size="sm">
          <Link href="/portal">Back to Portal</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto py-8">
      {/* Animated check */}
      <div className="flex justify-center mb-6">
        <div
          className={cn(
            "h-24 w-24 rounded-full flex items-center justify-center",
            "bg-success-light border-4 border-success/20",
            "animate-[scale-in_0.4s_ease-out]"
          )}
          style={{ animation: "scaleIn 0.4s ease-out" }}
        >
          <CheckCircle2 className="h-12 w-12 text-success" />
        </div>
      </div>

      {/* Heading */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-text-primary mb-2">
          Interview Complete!
        </h1>
        <p className="text-text-muted max-w-sm mx-auto leading-relaxed">
          Great job! Your responses are being evaluated. You&apos;ll receive your
          assessment report shortly.
        </p>
      </div>

      {/* Quick stats */}
      <Card className="mb-5">
        <CardContent className="p-5">
          <h2 className="text-sm font-semibold text-text-primary mb-4">
            Interview Summary
          </h2>
          <div className="grid grid-cols-2 gap-4">
            {stats.map((stat) => (
              <div key={stat.label} className="flex items-start gap-3">
                <div className="h-9 w-9 rounded-lg bg-bg flex items-center justify-center shrink-0">
                  <stat.icon className="h-4 w-4 text-text-muted" />
                </div>
                <div>
                  <p className={cn("text-lg font-bold", stat.color)}>
                    {stat.value}
                  </p>
                  <p className="text-xs text-text-muted">{stat.label}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Next steps */}
      <Card className="mb-6">
        <CardContent className="p-5">
          <h2 className="text-sm font-semibold text-text-primary mb-4">
            What Happens Next
          </h2>
          <div className="space-y-4">
            {NEXT_STEPS.map((step, i) => (
              <div key={i} className="flex items-start gap-3">
                <div
                  className={cn(
                    "h-9 w-9 rounded-lg flex items-center justify-center shrink-0",
                    step.color
                  )}
                >
                  <step.icon className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-text-primary">
                    {step.title}
                  </p>
                  <p className="text-xs text-text-muted mt-0.5">
                    {step.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Report button */}
      <div className="space-y-3">
        {reportReady ? (
          <Button asChild size="lg" className="w-full">
            <Link href={`/interview/${token}/report`}>
              <FileText className="h-4 w-4" />
              View Your Report
            </Link>
          </Button>
        ) : (
          <Button disabled size="lg" className="w-full" loading>
            Report generating... (LLM analysis in progress)
          </Button>
        )}

        {error && (
          <div className="text-center text-xs text-warning mt-2 font-medium">
            {error} You can still try refreshing later.
          </div>
        )}

        <div className="text-center mt-4">
          <Link
            href={`/portal?token=${token}`}
            className="inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-text-primary transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Return to Portal
          </Link>
        </div>
      </div>

      <style jsx>{`
        @keyframes scaleIn {
          0% { transform: scale(0.5); opacity: 0; }
          60% { transform: scale(1.1); }
          100% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
