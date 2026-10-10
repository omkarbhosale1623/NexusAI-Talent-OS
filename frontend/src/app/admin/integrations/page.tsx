"use client";

import { useEffect, useState } from "react";
import {
  Plug,
  Calendar as CalendarIcon,
  MessageSquare,
  Code2,
  UploadCloud,
  Loader2,
  CheckCircle2,
  XCircle,
  Copy,
  Trash2,
  RefreshCw,
} from "lucide-react";
import AdminLayout from "@/components/layout/admin-layout";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

// ── helpers ────────────────────────────────────────────────────────────────
function errMsg(e: unknown): string {
  if (e instanceof Error) return e.message;
  return "Something went wrong. This feature may be disabled.";
}

function asArray<T = any>(data: any): T[] {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.items)) return data.items;
  if (data && Array.isArray(data.connections)) return data.connections;
  if (data && Array.isArray(data.results)) return data.results;
  return [];
}

function maskKey(k?: string): string {
  if (!k) return "";
  if (k.length <= 4) return "••••";
  return "••••••••" + k.slice(-4);
}

const Spinner = () => (
  <div className="flex items-center justify-center gap-2 py-8 text-text-muted">
    <Loader2 className="h-4 w-4 animate-spin" />
    <span className="text-sm">Loading…</span>
  </div>
);

const Notice = ({
  kind = "muted",
  children,
}: {
  kind?: "muted" | "error" | "success";
  children: React.ReactNode;
}) => (
  <div
    className={cn(
      "rounded-lg px-3.5 py-2.5 text-sm",
      kind === "error" && "bg-error-light text-error",
      kind === "success" && "bg-success-light text-success",
      kind === "muted" && "bg-bg text-text-muted border border-border"
    )}
  >
    {children}
  </div>
);

// ─────────────────────────────────────────────────────────────────────────────
// ATS TAB
// ─────────────────────────────────────────────────────────────────────────────
const ATS_PROVIDERS = [
  { id: "greenhouse", label: "Greenhouse" },
  { id: "lever", label: "Lever" },
  { id: "workday", label: "Workday" },
];

function AtsProviderCard({
  provider,
  label,
  connection,
  onChanged,
}: {
  provider: string;
  label: string;
  connection: any | null;
  onChanged: () => void;
}) {
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState(connection?.base_url ?? "");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [feedback, setFeedback] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  const [jobs, setJobs] = useState<any[] | null>(null);

  const connected = !!connection;

  async function handleSave() {
    setFeedback(null);
    if (!apiKey.trim()) {
      setFeedback({ kind: "error", text: "API key is required." });
      return;
    }
    setSaving(true);
    try {
      await api.saveAtsConnection({
        provider,
        api_key: apiKey.trim(),
        base_url: baseUrl.trim() || undefined,
      });
      setApiKey("");
      setFeedback({ kind: "success", text: "Connection saved." });
      onChanged();
    } catch (e) {
      setFeedback({ kind: "error", text: errMsg(e) });
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    setFeedback(null);
    setTesting(true);
    try {
      const res: any = await api.testAts(provider);
      const ok = res?.ok ?? res?.success ?? true;
      setFeedback({
        kind: ok ? "success" : "error",
        text: ok ? "Connection test passed." : res?.error || res?.message || "Test failed.",
      });
    } catch (e) {
      setFeedback({ kind: "error", text: errMsg(e) });
    } finally {
      setTesting(false);
    }
  }

  async function handleDelete() {
    if (!connection?.id) return;
    setFeedback(null);
    try {
      await api.deleteAtsConnection(connection.id);
      setJobs(null);
      onChanged();
    } catch (e) {
      setFeedback({ kind: "error", text: errMsg(e) });
    }
  }

  async function handleListJobs() {
    setFeedback(null);
    setLoadingJobs(true);
    try {
      const data = await api.listAtsJobs(provider);
      setJobs(asArray(data));
    } catch (e) {
      setJobs(null);
      setFeedback({ kind: "error", text: errMsg(e) });
    } finally {
      setLoadingJobs(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{label}</CardTitle>
          {connected ? (
            <Badge variant="success">Connected</Badge>
          ) : (
            <Badge variant="outline">Not connected</Badge>
          )}
        </div>
        {connected && connection?.api_key && (
          <CardDescription>Key: {maskKey(connection.api_key)}</CardDescription>
        )}
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <Input
          label="API Key"
          type="password"
          placeholder={connected ? "Enter a new key to replace" : "Paste API key"}
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
        />
        <Input
          label="Base URL (optional)"
          placeholder="https://api.example.com"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
        />

        <div className="flex flex-wrap items-center gap-2 pt-1">
          <Button size="sm" loading={saving} onClick={handleSave}>
            Save
          </Button>
          <Button
            size="sm"
            variant="secondary"
            loading={testing}
            disabled={!connected}
            onClick={handleTest}
          >
            Test
          </Button>
          <Button
            size="sm"
            variant="ghost"
            loading={loadingJobs}
            disabled={!connected}
            onClick={handleListJobs}
          >
            List Jobs
          </Button>
          {connected && (
            <Button size="sm" variant="danger" onClick={handleDelete}>
              <Trash2 className="h-4 w-4" /> Remove
            </Button>
          )}
        </div>

        {feedback && (
          <Notice kind={feedback.kind}>
            <span className="inline-flex items-center gap-1.5">
              {feedback.kind === "success" ? (
                <CheckCircle2 className="h-4 w-4" />
              ) : (
                <XCircle className="h-4 w-4" />
              )}
              {feedback.text}
            </span>
          </Notice>
        )}

        {jobs && (
          <div className="rounded-lg border border-border bg-bg p-3">
            <p className="text-sm font-medium text-text-primary">
              {jobs.length} job{jobs.length === 1 ? "" : "s"} found
            </p>
            {jobs.length > 0 ? (
              <ul className="mt-2 flex flex-col gap-1">
                {jobs.slice(0, 5).map((j: any, i: number) => (
                  <li key={j.id ?? i} className="text-sm text-text-muted">
                    • {j.title ?? j.name ?? `Job ${j.id ?? i + 1}`}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-1 text-sm text-text-muted">No jobs returned.</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function AtsTab() {
  const [connections, setConnections] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listAtsConnections();
      setConnections(asArray(data));
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (loading) return <Spinner />;

  return (
    <div className="flex flex-col gap-4">
      {error && <Notice kind="error">{error}</Notice>}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {ATS_PROVIDERS.map((p) => {
          const conn =
            connections.find(
              (c) => (c.provider ?? "").toLowerCase() === p.id
            ) ?? null;
          return (
            <AtsProviderCard
              key={p.id}
              provider={p.id}
              label={p.label}
              connection={conn}
              onChanged={load}
            />
          );
        })}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// CALENDAR TAB
// ─────────────────────────────────────────────────────────────────────────────
function CalendarTab() {
  const [connections, setConnections] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listCalendarConnections();
      setConnections(asArray(data));
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function connect(which: "google" | "outlook") {
    setError(null);
    setConnecting(which);
    try {
      const res: any =
        which === "google"
          ? await api.connectGoogleCalendar()
          : await api.connectOutlookCalendar();
      if (res?.ok && res?.auth_url) {
        window.location.href = res.auth_url;
        return;
      }
      setError(res?.message || res?.error || "OAuth is not available. Server credentials may be required.");
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setConnecting(null);
    }
  }

  async function disconnect(id: string) {
    setError(null);
    try {
      await api.deleteCalendarConnection(id);
      load();
    } catch (e) {
      setError(errMsg(e));
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Connect a calendar</CardTitle>
          <CardDescription>
            Sync interview scheduling. OAuth requires server credentials to be configured.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button
            loading={connecting === "google"}
            onClick={() => connect("google")}
          >
            <CalendarIcon className="h-4 w-4" /> Connect Google
          </Button>
          <Button
            variant="secondary"
            loading={connecting === "outlook"}
            onClick={() => connect("outlook")}
          >
            <CalendarIcon className="h-4 w-4" /> Connect Outlook
          </Button>
        </CardContent>
      </Card>

      {error && <Notice kind="error">{error}</Notice>}

      <Card>
        <CardHeader>
          <CardTitle>Connected calendars</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <Spinner />
          ) : connections.length === 0 ? (
            <Notice>No calendars connected yet.</Notice>
          ) : (
            <ul className="flex flex-col divide-y divide-border">
              {connections.map((c, i) => (
                <li
                  key={c.id ?? i}
                  className="flex items-center justify-between py-3 first:pt-0 last:pb-0"
                >
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-text-primary capitalize">
                      {c.provider ?? "Calendar"}
                    </span>
                    <span className="text-sm text-text-muted">
                      {c.email ?? c.account ?? "Connected"}
                    </span>
                  </div>
                  {c.id && (
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => disconnect(c.id)}
                    >
                      Disconnect
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SMS TAB
// ─────────────────────────────────────────────────────────────────────────────
function SmsTab() {
  const [to, setTo] = useState("");
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [feedback, setFeedback] = useState<{ kind: "error" | "success"; text: string } | null>(null);

  const [messages, setMessages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  async function loadMessages() {
    setLoading(true);
    setListError(null);
    try {
      const data = await api.listMessages();
      setMessages(asArray(data));
    } catch (e) {
      setListError(errMsg(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMessages();
  }, []);

  async function handleSend() {
    setFeedback(null);
    if (!to.trim() || !body.trim()) {
      setFeedback({ kind: "error", text: "Recipient number and message are required." });
      return;
    }
    setSending(true);
    try {
      await api.sendSms(to.trim(), body.trim());
      setFeedback({ kind: "success", text: "Message sent." });
      setBody("");
      loadMessages();
    } catch (e) {
      setFeedback({ kind: "error", text: errMsg(e) });
    } finally {
      setSending(false);
    }
  }

  function statusBadge(status?: string) {
    const s = (status ?? "").toLowerCase();
    if (["delivered", "sent", "success"].includes(s)) return <Badge variant="success">{status}</Badge>;
    if (["failed", "error", "undelivered"].includes(s)) return <Badge variant="error">{status}</Badge>;
    return <Badge variant="muted">{status ?? "—"}</Badge>;
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Send an SMS</CardTitle>
          <CardDescription>Send a one-off message to a candidate.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <Input
            label="To (phone number)"
            placeholder="+1 555 123 4567"
            value={to}
            onChange={(e) => setTo(e.target.value)}
          />
          <Textarea
            label="Message"
            placeholder="Type your message…"
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
          <div>
            <Button loading={sending} onClick={handleSend}>
              Send SMS
            </Button>
          </div>
          {feedback && (
            <Notice kind={feedback.kind}>{feedback.text}</Notice>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Recent messages</CardTitle>
            <Button size="sm" variant="ghost" onClick={loadMessages}>
              <RefreshCw className="h-4 w-4" /> Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <Spinner />
          ) : listError ? (
            <Notice kind="error">{listError}</Notice>
          ) : messages.length === 0 ? (
            <Notice>No messages yet.</Notice>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-text-muted">
                    <th className="py-2 pr-4 font-medium">To</th>
                    <th className="py-2 pr-4 font-medium">Status</th>
                    <th className="py-2 font-medium">Sent</th>
                  </tr>
                </thead>
                <tbody>
                  {messages.map((m, i) => (
                    <tr key={m.id ?? i} className="border-b border-border last:border-0">
                      <td className="py-2.5 pr-4 text-text-primary">
                        {m.to_address ?? m.to ?? "—"}
                      </td>
                      <td className="py-2.5 pr-4">{statusBadge(m.status)}</td>
                      <td className="py-2.5 text-text-muted">
                        {m.created_at
                          ? new Date(m.created_at).toLocaleString()
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// WIDGET TAB
// ─────────────────────────────────────────────────────────────────────────────
function WidgetTab() {
  const [snippet, setSnippet] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const me: any = await api.me();
        const orgId = me?.org_id ?? me?.organization_id;
        if (!orgId) throw new Error("Could not determine your organization.");
        const data: any = await api.getWidgetEmbed(orgId);
        const snip =
          typeof data === "string"
            ? data
            : data?.snippet ?? data?.embed ?? data?.code ?? "";
        if (active) setSnippet(snip || "");
      } catch (e) {
        if (active) setError(errMsg(e));
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function copy() {
    try {
      await navigator.clipboard.writeText(snippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Could not copy to clipboard.");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>White-label embed widget</CardTitle>
        <CardDescription>
          Paste this snippet into your careers site to embed the branded
          application and interview widget. It is scoped to your organization.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {loading ? (
          <Spinner />
        ) : error ? (
          <Notice kind="error">{error}</Notice>
        ) : !snippet ? (
          <Notice>No embed snippet available.</Notice>
        ) : (
          <>
            <textarea
              readOnly
              value={snippet}
              rows={6}
              className="w-full rounded-lg border border-input-border bg-bg px-3.5 py-3 font-mono text-xs text-text-primary focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
            />
            <div>
              <Button variant="secondary" onClick={copy}>
                <Copy className="h-4 w-4" />
                {copied ? "Copied!" : "Copy"}
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// BULK UPLOAD TAB
// ─────────────────────────────────────────────────────────────────────────────
function BulkTab() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [jobId, setJobId] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [jobsError, setJobsError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);

  useEffect(() => {
    (async () => {
      setLoadingJobs(true);
      setJobsError(null);
      try {
        const data = await api.listJobs();
        setJobs(asArray(data));
      } catch (e) {
        setJobsError(errMsg(e));
      } finally {
        setLoadingJobs(false);
      }
    })();
  }, []);

  async function handleUpload() {
    setError(null);
    setResult(null);
    if (!jobId) {
      setError("Please select a job.");
      return;
    }
    if (files.length === 0) {
      setError("Please choose at least one file.");
      return;
    }
    setUploading(true);
    try {
      const res = await api.bulkUpload(jobId, files);
      setResult(res);
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setUploading(false);
    }
  }

  const rows = result ? asArray(result) : [];

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Bulk resume upload</CardTitle>
          <CardDescription>
            Upload multiple resumes at once and auto-create candidates against a job.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-text-primary">Job</label>
            {loadingJobs ? (
              <Spinner />
            ) : jobsError ? (
              <Notice kind="error">{jobsError}</Notice>
            ) : (
              <select
                value={jobId}
                onChange={(e) => setJobId(e.target.value)}
                className="h-11 w-full rounded-lg border border-input-border bg-surface px-3.5 text-sm text-text-primary focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
              >
                <option value="">Select a job…</option>
                {jobs.map((j, i) => (
                  <option key={j.id ?? i} value={j.id}>
                    {j.title ?? j.name ?? `Job ${j.id}`}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-text-primary">
              Resume files
            </label>
            <input
              type="file"
              multiple
              accept=".pdf,.docx,.doc"
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
              className="block w-full text-sm text-text-muted file:mr-3 file:rounded-full file:border-0 file:bg-brand-light file:px-4 file:py-2 file:text-sm file:font-semibold file:text-brand hover:file:bg-brand-light/70"
            />
            {files.length > 0 && (
              <p className="text-xs text-text-muted">
                {files.length} file{files.length === 1 ? "" : "s"} selected
              </p>
            )}
          </div>

          <div>
            <Button loading={uploading} onClick={handleUpload}>
              <UploadCloud className="h-4 w-4" /> Upload
            </Button>
          </div>

          {error && <Notice kind="error">{error}</Notice>}
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Upload results</CardTitle>
            <CardDescription>
              Total {result.total ?? rows.length} · Succeeded{" "}
              {result.succeeded ?? "—"} · Failed {result.failed ?? "—"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {rows.length === 0 ? (
              <Notice>No detailed results returned.</Notice>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-text-muted">
                      <th className="py-2 pr-4 font-medium">File</th>
                      <th className="py-2 pr-4 font-medium">Status</th>
                      <th className="py-2 pr-4 font-medium">Score</th>
                      <th className="py-2 font-medium">Detail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r: any, i: number) => {
                      const ok = !r.error && (r.status ?? "").toLowerCase() !== "failed";
                      return (
                        <tr key={i} className="border-b border-border last:border-0">
                          <td className="py-2.5 pr-4 text-text-primary">
                            {r.filename ?? `File ${i + 1}`}
                          </td>
                          <td className="py-2.5 pr-4">
                            {ok ? (
                              <Badge variant="success">{r.status ?? "ok"}</Badge>
                            ) : (
                              <Badge variant="error">{r.status ?? "failed"}</Badge>
                            )}
                          </td>
                          <td className="py-2.5 pr-4 text-text-muted">
                            {r.score != null ? r.score : "—"}
                          </td>
                          <td className="py-2.5 text-text-muted">
                            {r.error ?? r.candidate_id ?? "—"}
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
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// PAGE
// ─────────────────────────────────────────────────────────────────────────────
const TABS = [
  { value: "ats", label: "ATS", icon: Plug },
  { value: "calendar", label: "Calendar", icon: CalendarIcon },
  { value: "sms", label: "SMS", icon: MessageSquare },
  { value: "widget", label: "Widget", icon: Code2 },
  { value: "bulk", label: "Bulk Upload", icon: UploadCloud },
];

export default function IntegrationsPage() {
  return (
    <AdminLayout title="Integrations">
      <div className="mx-auto max-w-5xl">
        <Tabs defaultValue="ats">
          <TabsList className="flex-wrap">
            {TABS.map((t) => {
              const Icon = t.icon;
              return (
                <TabsTrigger key={t.value} value={t.value}>
                  <span className="inline-flex items-center gap-1.5">
                    <Icon className="h-4 w-4" />
                    {t.label}
                  </span>
                </TabsTrigger>
              );
            })}
          </TabsList>

          <TabsContent value="ats">
            <AtsTab />
          </TabsContent>
          <TabsContent value="calendar">
            <CalendarTab />
          </TabsContent>
          <TabsContent value="sms">
            <SmsTab />
          </TabsContent>
          <TabsContent value="widget">
            <WidgetTab />
          </TabsContent>
          <TabsContent value="bulk">
            <BulkTab />
          </TabsContent>
        </Tabs>
      </div>
    </AdminLayout>
  );
}
