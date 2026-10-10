"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Briefcase,
  Calendar,
  Clock,
  Video,
  FileText,
  Check,
  AlertCircle,
  HelpCircle
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { formatDate, cn } from "@/lib/utils";
import { api } from "@/lib/api";

const PIPELINE_STEPS = [
  { key: "applied", label: "Applied" },
  { key: "shortlisted", label: "Screening" },
  { key: "invited", label: "Invited" },
  { key: "scheduled", label: "Scheduled" },
  { key: "completed", label: "Completed" },
];

const STATUS_STEP_INDEX: Record<string, number> = {
  applied: 0,
  screening: 1,
  shortlisted: 1,
  invited: 2,
  scheduled: 3,
  interview_scheduled: 3,
  in_progress: 3,
  interview_completed: 4,
  completed: 4,
  evaluated: 4,
  hired: 4,
  rejected: -1,
};

function PipelineProgress({ status }: { status: string }) {
  const currentStep = STATUS_STEP_INDEX[status] ?? 0;
  const isRejected = status === "rejected";

  if (isRejected) {
    return (
      <p className="text-xs text-error font-medium">Application not selected</p>
    );
  }

  return (
    <div className="flex items-center gap-0">
      {PIPELINE_STEPS.map((step, i) => {
        const done = i < currentStep;
        const active = i === currentStep;
        const last = i === PIPELINE_STEPS.length - 1;

        return (
          <div key={step.key} className="flex items-center">
            <div className="flex flex-col items-center gap-1">
              <div
                className={cn(
                  "h-5 w-5 rounded-full flex items-center justify-center transition-colors",
                  done && "bg-brand",
                  active && "bg-brand ring-2 ring-brand/30 ring-offset-1",
                  !done && !active && "bg-border"
                )}
              >
                {done ? (
                  <Check className="h-2.5 w-2.5 text-white" strokeWidth={3} />
                ) : (
                  <div
                    className={cn(
                      "h-2 w-2 rounded-full",
                      active ? "bg-white" : "bg-text-muted/40"
                    )}
                  />
                )}
              </div>
              <span
                className={cn(
                  "text-[10px] leading-none whitespace-nowrap",
                  active
                    ? "text-brand font-semibold"
                    : done
                    ? "text-text-muted"
                    : "text-text-muted/60"
                )}
              >
                {step.label}
              </span>
            </div>
            {!last && (
              <div
                className={cn(
                  "h-px w-6 sm:w-10 mb-4 mx-0.5 transition-colors",
                  i < currentStep ? "bg-brand" : "bg-border"
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

function PortalContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const [portal, setPortal] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    api.getCandidatePortal(token)
      .then((data) => {
        setPortal(data);
      })
      .catch((err) => {
        console.error("Portal error:", err);
        setError("Invalid or expired candidate access token. Please check the link from your email.");
      })
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !token) {
    return (
      <div className="max-w-md mx-auto text-center py-12">
        <AlertCircle className="h-12 w-12 text-error mx-auto mb-4" />
        <h1 className="text-xl font-bold text-text-primary mb-2">Access Restrained</h1>
        <p className="text-sm text-text-muted mb-6">
          {error || "Please use the unique link sent to your email to access the candidate portal."}
        </p>
        <Button asChild size="sm">
          <Link href="/jobs">Browse Jobs</Link>
        </Button>
      </div>
    );
  }

  if (!portal) {
    return (
      <EmptyState
        icon={HelpCircle}
        title="Portal details unavailable"
        description="We couldn't retrieve application details at this time."
      />
    );
  }

  // Map backend status to corresponding pipeline values for UI
  const displayStatus = portal.application_status === "interview_scheduled" ? "scheduled" : portal.application_status;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">
          Welcome, {portal.candidate_name}
        </h1>
        <p className="text-sm text-text-muted mt-0.5">
          Track your application progress and manage your upcoming steps for {portal.company_name}.
        </p>
      </div>

      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col gap-6">
            {/* Job title & company */}
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-text-primary leading-snug">
                  {portal.job_title}
                </h2>
                <p className="text-sm text-text-muted mt-0.5">
                  {portal.company_name}
                </p>
              </div>
              <StatusBadge status={displayStatus} className="shrink-0" />
            </div>

            {/* Pipeline progress bar */}
            <div className="py-2 border-t border-b border-border">
              <p className="text-xs font-semibold text-text-primary uppercase tracking-wider mb-3">
                Application Stage
              </p>
              <PipelineProgress status={portal.application_status} />
            </div>

            {/* Scheduled date */}
            {portal.interview_scheduled_at && (
              <div className="flex items-center gap-2 text-sm text-text-primary bg-bg p-3 rounded-lg border border-border">
                <Calendar className="h-4 w-4 text-brand shrink-0" />
                <span className="font-medium">
                  Interview Scheduled: {formatDate(portal.interview_scheduled_at)} at{" "}
                  {new Date(portal.interview_scheduled_at).toLocaleTimeString("en-US", {
                    hour: "numeric",
                    minute: "2-digit",
                    hour12: true,
                  })}
                </span>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex flex-col gap-3 mt-2">
              {portal.can_schedule && (
                <Button asChild size="lg" className="w-full">
                  <Link href={`/schedule/${token}`}>
                    <Calendar className="mr-2 h-4 w-4" />
                    Schedule Your Voice AI Interview
                  </Link>
                </Button>
              )}

              {portal.can_join_interview && (
                <Button asChild size="lg" className="w-full animate-pulse">
                  <Link href={`/interview/${token}/prep`}>
                    <Video className="mr-2 h-4 w-4" />
                    Join Live Interview Room
                  </Link>
                </Button>
              )}

              {portal.can_view_report && portal.report_shared && (
                <Button asChild variant="secondary" size="lg" className="w-full">
                  <Link href={`/interview/${token}/report`}>
                    <FileText className="mr-2 h-4 w-4" />
                    View Interview Performance Report
                  </Link>
                </Button>
              )}

              {portal.application_status === "completed" && !portal.report_shared && (
                <div className="text-sm text-text-muted bg-warning-light/30 border border-warning/10 p-4 rounded-lg">
                  <p className="font-medium text-warning">Evaluation Pending</p>
                  <p className="text-xs text-text-muted mt-0.5 leading-relaxed">
                    Your interview response was submitted successfully. The hiring team is evaluating your results and will get back to you shortly.
                  </p>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function CandidatePortalPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <PortalContent />
    </Suspense>
  );
}
