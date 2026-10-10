"use client";

import { useState, useEffect, useCallback, use } from "react";
import Link from "next/link";
import {
  Camera,
  Mic,
  Wifi,
  Globe,
  CheckCircle2,
  XCircle,
  Loader2,
  Calendar,
  Clock,
  Layers,
  ChevronRight,
  AlertCircle,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

type CheckStatus = "idle" | "checking" | "passed" | "failed";

interface SystemCheck {
  id: string;
  icon: typeof Camera;
  title: string;
  description: string;
  result?: string;
}

const CHECKS: SystemCheck[] = [
  {
    id: "camera",
    icon: Camera,
    title: "Camera Check",
    description: "Allow camera access to ensure you're visible during the interview",
  },
  {
    id: "microphone",
    icon: Mic,
    title: "Microphone Check",
    description: "Allow microphone access so the AI can hear your responses",
  },
  {
    id: "internet",
    icon: Wifi,
    title: "Internet Speed",
    description: "Checking your connection stability for a smooth interview",
  },
  {
    id: "browser",
    icon: Globe,
    title: "Browser Check",
    description: "Verifying your browser supports all required features",
  },
];

const MOCK_RESULTS: Record<string, string> = {
  camera: "Camera detected — Preview active",
  microphone: "Microphone detected — Audio level good",
  internet: "32 Mbps — Good connection",
  browser: "Chrome 123 — Fully supported",
};

const INTERVIEW_INFO = {
  jobTitle: "Senior Frontend Engineer",
  company: "Stripe",
  date: "Sat, Mar 15, 2026",
  time: "2:00 PM",
  duration: 45,
  rounds: ["Introduction", "Technical", "Behavioral", "HR & Culture"],
};

export default function PrepPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const [statuses, setStatuses] = useState<Record<string, CheckStatus>>({
    camera: "idle",
    microphone: "idle",
    internet: "idle",
    browser: "idle",
  });
  const [audioLevel, setAudioLevel] = useState(0);
  const [activeCheckId, setActiveCheckId] = useState<string | null>(null);
  const [allPassed, setAllPassed] = useState(false);
  const [autoRunDone, setAutoRunDone] = useState(false);

  // Simulate audio level animation when mic is checking/passed
  useEffect(() => {
    if (statuses.microphone === "checking" || statuses.microphone === "passed") {
      const interval = setInterval(() => {
        setAudioLevel(Math.floor(Math.random() * 70) + 20);
      }, 150);
      return () => clearInterval(interval);
    } else {
      setAudioLevel(0);
    }
  }, [statuses.microphone]);

  // Check if all passed
  useEffect(() => {
    const all = CHECKS.every((c) => statuses[c.id] === "passed");
    setAllPassed(all);
  }, [statuses]);

  const runCheck = useCallback(async (checkId: string) => {
    setActiveCheckId(checkId);
    setStatuses((prev) => ({ ...prev, [checkId]: "checking" }));

    // Simulate check delay
    const delays: Record<string, number> = {
      camera: 1800,
      microphone: 2200,
      internet: 2500,
      browser: 800,
    };
    await new Promise((r) => setTimeout(r, delays[checkId] ?? 1500));

    // All pass in mock
    setStatuses((prev) => ({ ...prev, [checkId]: "passed" }));
    setActiveCheckId(null);
  }, []);

  // Auto-run all checks on mount
  useEffect(() => {
    if (autoRunDone) return;
    setAutoRunDone(true);

    const run = async () => {
      for (const check of CHECKS) {
        await runCheck(check.id);
        await new Promise((r) => setTimeout(r, 300));
      }
    };
    run();
  }, [autoRunDone, runCheck]);

  const passedCount = CHECKS.filter((c) => statuses[c.id] === "passed").length;
  const progress = (passedCount / CHECKS.length) * 100;

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary">System Check</h1>
        <p className="text-sm text-text-muted mt-1">
          Make sure everything works before your interview
        </p>
      </div>

      {/* Overall progress */}
      <Card className="mb-5">
        <CardContent className="p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-text-primary">
              {passedCount} of {CHECKS.length} checks passed
            </span>
            {allPassed && (
              <span className="text-xs font-semibold text-success flex items-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5" />
                All systems ready!
              </span>
            )}
          </div>
          <Progress value={progress} />
        </CardContent>
      </Card>

      {/* Checks */}
      <div className="space-y-3 mb-5">
        {CHECKS.map((check, index) => {
          const status = statuses[check.id];
          const isActive = activeCheckId === check.id;

          return (
            <Card
              key={check.id}
              className={cn(
                "transition-colors",
                status === "passed" && "border-success/30",
                status === "failed" && "border-error/30",
                isActive && "border-brand/40"
              )}
            >
              <CardContent className="p-5">
                <div className="flex items-start gap-4">
                  {/* Icon + status */}
                  <div className="relative shrink-0">
                    <div
                      className={cn(
                        "h-11 w-11 rounded-full flex items-center justify-center transition-colors",
                        status === "passed" && "bg-success-light",
                        status === "failed" && "bg-error-light",
                        status === "checking" && "bg-brand-light",
                        status === "idle" && "bg-bg"
                      )}
                    >
                      <check.icon
                        className={cn(
                          "h-5 w-5",
                          status === "passed" && "text-success",
                          status === "failed" && "text-error",
                          status === "checking" && "text-brand",
                          status === "idle" && "text-text-muted"
                        )}
                      />
                    </div>
                    {/* Status overlay */}
                    {status === "passed" && (
                      <div className="absolute -bottom-0.5 -right-0.5 h-4 w-4 rounded-full bg-success-light border-2 border-surface flex items-center justify-center">
                        <Check className="h-2 w-2 text-success" strokeWidth={3} />
                      </div>
                    )}
                    {status === "failed" && (
                      <div className="absolute -bottom-0.5 -right-0.5 h-4 w-4 rounded-full bg-error-light border-2 border-surface flex items-center justify-center">
                        <XCircle className="h-2.5 w-2.5 text-error" />
                      </div>
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="text-sm font-semibold text-text-primary">
                        {check.title}
                      </h3>
                      <StatusChip status={status} />
                    </div>
                    <p className="text-xs text-text-muted mt-0.5">
                      {check.description}
                    </p>

                    {/* Camera preview */}
                    {check.id === "camera" && status !== "idle" && (
                      <div
                        className={cn(
                          "mt-3 h-20 rounded-lg border border-border flex items-center justify-center",
                          status === "passed"
                            ? "bg-gray-900"
                            : "bg-bg animate-pulse"
                        )}
                      >
                        {status === "passed" ? (
                          <div className="flex items-center gap-2 text-white/70">
                            <Camera className="h-4 w-4" />
                            <span className="text-xs">Camera preview active</span>
                          </div>
                        ) : (
                          <Loader2 className="h-5 w-5 text-text-muted animate-spin" />
                        )}
                      </div>
                    )}

                    {/* Mic level */}
                    {check.id === "microphone" && status !== "idle" && (
                      <div className="mt-3">
                        <p className="text-xs text-text-muted mb-1.5">
                          Audio level
                        </p>
                        <div className="flex items-end gap-0.5 h-8">
                          {Array.from({ length: 24 }).map((_, i) => {
                            const threshold = (i / 24) * 100;
                            const active = audioLevel > threshold;
                            return (
                              <div
                                key={i}
                                className={cn(
                                  "flex-1 rounded-sm transition-all duration-75",
                                  active
                                    ? i > 18
                                      ? "bg-error"
                                      : i > 12
                                      ? "bg-warning"
                                      : "bg-success"
                                    : "bg-border"
                                )}
                                style={{
                                  height: `${Math.min(100, 30 + (i / 24) * 70)}%`,
                                }}
                              />
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Result text */}
                    {status === "passed" && MOCK_RESULTS[check.id] && (
                      <p className="text-xs text-success mt-2 font-medium">
                        {MOCK_RESULTS[check.id]}
                      </p>
                    )}
                    {status === "failed" && (
                      <div className="mt-2 flex items-center gap-1.5">
                        <AlertCircle className="h-3.5 w-3.5 text-error" />
                        <p className="text-xs text-error">
                          Check failed.{" "}
                          <button
                            className="underline font-medium"
                            onClick={() => runCheck(check.id)}
                          >
                            Retry
                          </button>
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Interview info */}
      <Card className="mb-6 bg-brand-light/30 border-brand/20">
        <CardContent className="p-5">
          <h3 className="text-sm font-semibold text-brand mb-3">
            Your Interview Details
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-xs text-text-muted">Position</p>
              <p className="text-sm font-medium text-text-primary mt-0.5">
                {INTERVIEW_INFO.jobTitle}
              </p>
            </div>
            <div>
              <p className="text-xs text-text-muted">Company</p>
              <p className="text-sm font-medium text-text-primary mt-0.5">
                {INTERVIEW_INFO.company}
              </p>
            </div>
            <div>
              <p className="text-xs text-text-muted">Date & Time</p>
              <p className="text-sm font-medium text-text-primary mt-0.5">
                {INTERVIEW_INFO.date} · {INTERVIEW_INFO.time}
              </p>
            </div>
            <div>
              <p className="text-xs text-text-muted">Duration</p>
              <p className="text-sm font-medium text-text-primary mt-0.5">
                ~{INTERVIEW_INFO.duration} minutes
              </p>
            </div>
          </div>
          <div className="mt-3">
            <p className="text-xs text-text-muted mb-1.5">Rounds</p>
            <div className="flex flex-wrap gap-1.5">
              {INTERVIEW_INFO.rounds.map((r, i) => (
                <span
                  key={i}
                  className="text-xs bg-surface border border-brand/20 text-brand px-2 py-0.5 rounded-full font-medium"
                >
                  {i + 1}. {r}
                </span>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Start button */}
      <Button
        asChild={allPassed}
        disabled={!allPassed}
        size="lg"
        className="w-full"
      >
        {allPassed ? (
          <Link href={`/interview/${token}`}>
            Start Interview
            <ChevronRight className="h-5 w-5" />
          </Link>
        ) : (
          <span>
            {passedCount < CHECKS.length
              ? "Completing checks..."
              : "Fix issues to continue"}
          </span>
        )}
      </Button>

      {!allPassed && (
        <p className="text-center text-xs text-text-muted mt-3">
          All system checks must pass before starting your interview
        </p>
      )}
    </div>
  );
}

function StatusChip({ status }: { status: CheckStatus }) {
  if (status === "idle") return null;
  if (status === "checking") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-brand bg-brand-light px-2 py-0.5 rounded-full">
        <Loader2 className="h-3 w-3 animate-spin" />
        Checking
      </span>
    );
  }
  if (status === "passed") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-success bg-success-light px-2 py-0.5 rounded-full">
        <CheckCircle2 className="h-3 w-3" />
        Passed
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-error bg-error-light px-2 py-0.5 rounded-full">
      <XCircle className="h-3 w-3" />
      Failed
    </span>
  );
}

// Re-export Check icon used inline
function Check(props: React.SVGProps<SVGSVGElement> & { strokeWidth?: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}
