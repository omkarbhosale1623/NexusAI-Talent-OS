"use client";

import { useEffect, useMemo, useState } from "react";
import { Play, Send, AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

interface CodingProblem {
  id: string;
  title: string;
  prompt: string;
  starter_code?: { python?: string; javascript?: string } & Record<string, string>;
  language_default?: string;
  [key: string]: unknown;
}

interface RunResult {
  ok: boolean;
  stdout?: string;
  stderr?: string;
  exit_code?: number;
  runtime_ms?: number;
  submission_id?: string;
}

interface SubmitCase {
  passed: boolean;
  expected: unknown;
  got: unknown;
}

interface SubmitResult {
  submission_id: string;
  tests_passed: number;
  tests_total: number;
  score: number;
  cases: SubmitCase[];
  error?: string;
}

const LANGUAGES: { value: string; label: string }[] = [
  { value: "python", label: "Python" },
  { value: "javascript", label: "JavaScript" },
  { value: "java", label: "Java" },
  { value: "cpp", label: "C++" },
  { value: "go", label: "Go" },
];

const selectClass =
  "h-11 w-full rounded-lg border border-input-border bg-surface px-3.5 text-sm text-text-primary " +
  "transition-colors duration-100 focus:border-brand focus:ring-2 focus:ring-brand/20 focus:outline-none " +
  "disabled:cursor-not-allowed disabled:opacity-50";

function starterFor(problem: CodingProblem | undefined, language: string): string {
  if (!problem?.starter_code) return "";
  return problem.starter_code[language] ?? "";
}

function stringify(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export default function CodingEnvironment({
  interviewId,
  jobId,
}: {
  interviewId: string;
  jobId?: string;
}) {
  const [problems, setProblems] = useState<CodingProblem[]>([]);
  const [loadingProblems, setLoadingProblems] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [problemId, setProblemId] = useState<string>("");
  const [language, setLanguage] = useState<string>("python");
  const [source, setSource] = useState<string>("");
  const [stdin, setStdin] = useState<string>("");

  const [running, setRunning] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  const [submitResult, setSubmitResult] = useState<SubmitResult | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const selectedProblem = useMemo(
    () => problems.find((p) => p.id === problemId),
    [problems, problemId]
  );

  // Load problems on mount / when jobId changes.
  useEffect(() => {
    let cancelled = false;
    setLoadingProblems(true);
    setLoadError(null);
    api
      .listCodingProblems(jobId)
      .then((data: unknown) => {
        if (cancelled) return;
        const list = (Array.isArray(data) ? data : []) as CodingProblem[];
        setProblems(list);
        if (list.length > 0) {
          const first = list[0];
          setProblemId(first.id);
          const lang = first.language_default || "python";
          setLanguage(lang);
          setSource(starterFor(first, lang));
        }
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setLoadError(err instanceof Error ? err.message : "Failed to load problems");
      })
      .finally(() => {
        if (!cancelled) setLoadingProblems(false);
      });
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  function handleProblemChange(id: string) {
    setProblemId(id);
    setRunResult(null);
    setSubmitResult(null);
    setActionError(null);
    const next = problems.find((p) => p.id === id);
    const lang = next?.language_default || language;
    setLanguage(lang);
    setSource(starterFor(next, lang));
  }

  function handleLanguageChange(lang: string) {
    setLanguage(lang);
    // Refill starter only if we have one for the new language and the editor
    // is empty or still holds the previous starter (avoid clobbering real work).
    const prevStarter = starterFor(selectedProblem, language);
    const nextStarter = starterFor(selectedProblem, lang);
    if (nextStarter && (source.trim() === "" || source === prevStarter)) {
      setSource(nextStarter);
    }
  }

  function handleEditorKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key !== "Tab") return;
    e.preventDefault();
    const el = e.currentTarget;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    const next = source.slice(0, start) + "  " + source.slice(end);
    setSource(next);
    requestAnimationFrame(() => {
      el.selectionStart = el.selectionEnd = start + 2;
    });
  }

  async function handleRun() {
    setRunning(true);
    setActionError(null);
    setRunResult(null);
    try {
      const res = (await api.runCode(interviewId, {
        language,
        source,
        stdin: stdin || undefined,
        problem_id: problemId || undefined,
      })) as RunResult;
      setRunResult(res);
      if (res && res.ok === false && !res.stderr) {
        setActionError("Execution failed.");
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setRunning(false);
    }
  }

  async function handleSubmit() {
    if (!problemId) {
      setActionError("Select a problem before submitting.");
      return;
    }
    setSubmitting(true);
    setActionError(null);
    setSubmitResult(null);
    try {
      const res = (await api.submitCode(interviewId, {
        language,
        source,
        problem_id: problemId,
      })) as SubmitResult;
      setSubmitResult(res);
      if (res?.error) setActionError(res.error);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Submit failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* Left column: problem + selectors */}
      <div className="flex flex-col gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Problem</CardTitle>
            <CardDescription>
              Select a problem and language, then write your solution.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {loadingProblems ? (
              <p className="text-sm text-text-muted">Loading problems…</p>
            ) : loadError ? (
              <div className="flex items-start gap-2 rounded-lg bg-error-light p-3 text-sm text-error">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{loadError}</span>
              </div>
            ) : problems.length === 0 ? (
              <p className="text-sm text-text-muted">
                No coding problems available
                {jobId ? " for this job." : "."}
              </p>
            ) : (
              <>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-sm font-medium text-text-primary">
                      Problem
                    </label>
                    <select
                      className={selectClass}
                      value={problemId}
                      onChange={(e) => handleProblemChange(e.target.value)}
                    >
                      {problems.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.title}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-sm font-medium text-text-primary">
                      Language
                    </label>
                    <select
                      className={selectClass}
                      value={language}
                      onChange={(e) => handleLanguageChange(e.target.value)}
                    >
                      {LANGUAGES.map((l) => (
                        <option key={l.value} value={l.value}>
                          {l.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {selectedProblem && (
                  <div className="flex flex-col gap-2">
                    <h4 className="text-base font-semibold text-text-primary">
                      {selectedProblem.title}
                    </h4>
                    <p className="whitespace-pre-wrap text-sm leading-relaxed text-text-muted">
                      {selectedProblem.prompt}
                    </p>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Right column: editor + output */}
      <div className="flex flex-col gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Code Editor</CardTitle>
            <CardDescription>
              Tab inserts 2 spaces. Run against custom stdin or submit for grading.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <textarea
              value={source}
              onChange={(e) => setSource(e.target.value)}
              onKeyDown={handleEditorKeyDown}
              spellCheck={false}
              placeholder="// Write your solution here"
              className={cn(
                "min-h-[320px] w-full rounded-lg border border-input-border bg-surface p-4",
                "font-mono text-sm leading-relaxed text-text-primary placeholder:text-text-muted",
                "resize-y transition-colors duration-100",
                "focus:border-brand focus:ring-2 focus:ring-brand/20 focus:outline-none"
              )}
            />

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-text-primary">
                Standard input (optional)
              </label>
              <textarea
                value={stdin}
                onChange={(e) => setStdin(e.target.value)}
                spellCheck={false}
                placeholder="Input passed to your program on stdin"
                className={cn(
                  "min-h-[80px] w-full rounded-lg border border-input-border bg-surface p-3",
                  "font-mono text-sm text-text-primary placeholder:text-text-muted",
                  "resize-y transition-colors duration-100",
                  "focus:border-brand focus:ring-2 focus:ring-brand/20 focus:outline-none"
                )}
              />
            </div>

            <div className="flex flex-wrap gap-3">
              <Button
                variant="secondary"
                onClick={handleRun}
                loading={running}
                disabled={running || submitting}
              >
                {!running && <Play className="h-4 w-4" />}
                Run
              </Button>
              <Button
                onClick={handleSubmit}
                loading={submitting}
                disabled={running || submitting || !problemId}
              >
                {!submitting && <Send className="h-4 w-4" />}
                Submit
              </Button>
            </div>

            {actionError && (
              <div className="flex items-start gap-2 rounded-lg bg-error-light p-3 text-sm text-error">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Run output */}
        {runResult && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between gap-2">
                <CardTitle>Output</CardTitle>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={runResult.ok ? "success" : "error"}>
                    {runResult.ok ? "OK" : "Failed"}
                  </Badge>
                  {runResult.exit_code !== undefined && (
                    <Badge variant={runResult.exit_code === 0 ? "muted" : "warning"}>
                      exit {runResult.exit_code}
                    </Badge>
                  )}
                  {runResult.runtime_ms !== undefined && (
                    <Badge variant="muted">{runResult.runtime_ms} ms</Badge>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">
                  stdout
                </p>
                <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-bg p-3 font-mono text-xs text-text-primary">
                  {runResult.stdout || "(no output)"}
                </pre>
              </div>
              {runResult.stderr && (
                <div>
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">
                    stderr
                  </p>
                  <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-bg p-3 font-mono text-xs text-error">
                    {runResult.stderr}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Submit results */}
        {submitResult && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between gap-2">
                <CardTitle>Test Results</CardTitle>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge
                    variant={
                      submitResult.tests_passed === submitResult.tests_total &&
                      submitResult.tests_total > 0
                        ? "success"
                        : submitResult.tests_passed > 0
                          ? "warning"
                          : "error"
                    }
                  >
                    {submitResult.tests_passed}/{submitResult.tests_total} passed
                  </Badge>
                  <Badge variant="default">score {submitResult.score}</Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              {submitResult.error && (
                <div className="flex items-start gap-2 rounded-lg bg-error-light p-3 text-sm text-error">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{submitResult.error}</span>
                </div>
              )}
              {(submitResult.cases ?? []).map((c, i) => (
                <div
                  key={i}
                  className="flex flex-col gap-2 rounded-lg border border-border p-3"
                >
                  <div className="flex items-center gap-2">
                    {c.passed ? (
                      <CheckCircle2 className="h-4 w-4 text-success" />
                    ) : (
                      <XCircle className="h-4 w-4 text-error" />
                    )}
                    <span className="text-sm font-medium text-text-primary">
                      Test case {i + 1}
                    </span>
                    <span
                      className={cn(
                        "text-xs font-semibold",
                        c.passed ? "text-success" : "text-error"
                      )}
                    >
                      {c.passed ? "Passed" : "Failed"}
                    </span>
                  </div>
                  {!c.passed && (
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      <div>
                        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">
                          Expected
                        </p>
                        <pre className="overflow-auto whitespace-pre-wrap rounded-md border border-border bg-bg p-2 font-mono text-xs text-text-primary">
                          {stringify(c.expected)}
                        </pre>
                      </div>
                      <div>
                        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">
                          Got
                        </p>
                        <pre className="overflow-auto whitespace-pre-wrap rounded-md border border-border bg-bg p-2 font-mono text-xs text-error">
                          {stringify(c.got)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
