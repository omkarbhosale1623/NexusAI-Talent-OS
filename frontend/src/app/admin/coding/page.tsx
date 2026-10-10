"use client";

import { useState } from "react";
import { Info, RefreshCw } from "lucide-react";
import AdminLayout from "@/components/layout/admin-layout";
import CodingEnvironment from "@/components/interview/CodingEnvironment";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn, formatDate } from "@/lib/utils";
import { api } from "@/lib/api";

interface CodingSubmission {
  id?: string;
  submission_id?: string;
  problem_id?: string;
  problem_title?: string;
  language?: string;
  score?: number;
  tests_passed?: number;
  tests_total?: number;
  status?: string;
  created_at?: string;
}

function safeDate(value?: string): string {
  if (!value) return "—";
  try {
    return formatDate(value);
  } catch {
    return value;
  }
}

export default function CodingInterviewsPage() {
  const [interviewIdInput, setInterviewIdInput] = useState("");
  const [jobIdInput, setJobIdInput] = useState("");

  const [activeInterviewId, setActiveInterviewId] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | undefined>(undefined);

  const [submissions, setSubmissions] = useState<CodingSubmission[]>([]);
  const [loadingSubs, setLoadingSubs] = useState(false);
  const [subsError, setSubsError] = useState<string | null>(null);
  const [loadedFor, setLoadedFor] = useState<string | null>(null);

  async function loadSubmissions(iv: string) {
    setLoadingSubs(true);
    setSubsError(null);
    try {
      const data = (await api.listCodingSubmissions(iv)) as unknown;
      const list = (Array.isArray(data) ? data : []) as CodingSubmission[];
      setSubmissions(list);
      setLoadedFor(iv);
    } catch (err) {
      setSubmissions([]);
      setSubsError(err instanceof Error ? err.message : "Failed to load submissions");
    } finally {
      setLoadingSubs(false);
    }
  }

  function handleLoad() {
    const iv = interviewIdInput.trim();
    if (!iv) return;
    setActiveInterviewId(iv);
    setActiveJobId(jobIdInput.trim() || undefined);
    void loadSubmissions(iv);
  }

  return (
    <AdminLayout title="Coding Interviews">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        {/* Reviewer note */}
        <div className="flex items-start gap-2 rounded-lg bg-brand-light p-4 text-sm text-brand">
          <Info className="mt-0.5 h-4 w-4 shrink-0" />
          <p>
            Enter an interview ID to load the live coding environment. This page
            doubles as the reviewer view: it loads the same editor candidates use
            for demos and replays, plus a table of all past submissions for that
            interview.
          </p>
        </div>

        {/* Load controls */}
        <Card>
          <CardHeader>
            <CardTitle>Load interview</CardTitle>
            <CardDescription>
              Interview ID is required. Job ID is optional and filters the
              available coding problems.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
              <div className="flex-1">
                <Input
                  label="Interview ID"
                  placeholder="e.g. iv_123"
                  value={interviewIdInput}
                  onChange={(e) => setInterviewIdInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleLoad();
                  }}
                />
              </div>
              <div className="flex-1">
                <Input
                  label="Job ID (optional)"
                  placeholder="e.g. job_456"
                  value={jobIdInput}
                  onChange={(e) => setJobIdInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleLoad();
                  }}
                />
              </div>
              <Button onClick={handleLoad} disabled={!interviewIdInput.trim()}>
                Load
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Coding environment */}
        {activeInterviewId && (
          <CodingEnvironment
            key={`${activeInterviewId}:${activeJobId ?? ""}`}
            interviewId={activeInterviewId}
            jobId={activeJobId}
          />
        )}

        {/* Submissions viewer */}
        {activeInterviewId && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between gap-2">
                <div className="flex flex-col gap-1">
                  <CardTitle>Past submissions</CardTitle>
                  <CardDescription>
                    {loadedFor
                      ? `Submissions for interview ${loadedFor}`
                      : "Submission history"}
                  </CardDescription>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => loadSubmissions(activeInterviewId)}
                  loading={loadingSubs}
                  disabled={loadingSubs}
                >
                  {!loadingSubs && <RefreshCw className="h-4 w-4" />}
                  Refresh
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {loadingSubs ? (
                <p className="text-sm text-text-muted">Loading submissions…</p>
              ) : subsError ? (
                <p className="text-sm text-error">{subsError}</p>
              ) : submissions.length === 0 ? (
                <p className="text-sm text-text-muted">
                  No submissions yet for this interview.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-xs font-semibold uppercase tracking-wide text-text-muted">
                        <th className="px-3 py-2">Problem</th>
                        <th className="px-3 py-2">Language</th>
                        <th className="px-3 py-2">Score</th>
                        <th className="px-3 py-2">Tests</th>
                        <th className="px-3 py-2">Status</th>
                        <th className="px-3 py-2">Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {submissions.map((s, i) => {
                        const passed = s.tests_passed ?? 0;
                        const total = s.tests_total ?? 0;
                        const allPassed = total > 0 && passed === total;
                        return (
                          <tr
                            key={s.id ?? s.submission_id ?? i}
                            className="border-b border-border last:border-0"
                          >
                            <td className="px-3 py-2 text-text-primary">
                              {s.problem_title ?? s.problem_id ?? "—"}
                            </td>
                            <td className="px-3 py-2 font-mono text-text-muted">
                              {s.language ?? "—"}
                            </td>
                            <td className="px-3 py-2 text-text-primary">
                              {s.score ?? "—"}
                            </td>
                            <td className="px-3 py-2 text-text-muted">
                              {total > 0 ? `${passed}/${total}` : "—"}
                            </td>
                            <td className="px-3 py-2">
                              <Badge
                                variant={
                                  s.status
                                    ? allPassed
                                      ? "success"
                                      : passed > 0
                                        ? "warning"
                                        : "error"
                                    : "muted"
                                }
                              >
                                {s.status ??
                                  (total > 0
                                    ? allPassed
                                      ? "passed"
                                      : "partial"
                                    : "—")}
                              </Badge>
                            </td>
                            <td className="px-3 py-2 text-text-muted">
                              {safeDate(s.created_at)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {!activeInterviewId && (
          <p
            className={cn(
              "rounded-lg border border-dashed border-border p-8 text-center text-sm text-text-muted"
            )}
          >
            Enter an interview ID above and click Load to begin.
          </p>
        )}
      </div>
    </AdminLayout>
  );
}
