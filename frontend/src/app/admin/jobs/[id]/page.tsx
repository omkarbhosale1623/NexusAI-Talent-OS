"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Users,
  Search,
  MailPlus,
  Calendar,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar } from "@/components/ui/avatar";
import { StatusBadge } from "@/components/ui/status-badge";
import { ScoreBadge } from "@/components/ui/score-badge";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { cn, formatDate } from "@/lib/utils";
import { api } from "@/lib/api";
import { adaptJob, adaptApplication } from "@/lib/adapters";
import type { ApplicationStatus } from "@/types";

const STATUS_TABS: { key: ApplicationStatus | "all"; label: string }[] = [
  { key: "all", label: "All" },
  { key: "applied", label: "Applied" },
  { key: "shortlisted", label: "Shortlisted" },
  { key: "scheduled", label: "Scheduled" },
  { key: "completed", label: "Completed" },
  { key: "rejected", label: "Rejected" },
];

export default function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [job, setJob] = useState<any>(null);
  const [applications, setApplications] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | "all">("all");
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    Promise.all([
      api.getJob(id),
      api.listApplications({ job_id: id, page: 1, page_size: 100 }),
    ]).then(([j, apps]) => {
      setJob(adaptJob(j));
      setApplications((apps.items || []).map(adaptApplication));
    }).catch(console.error)
    .finally(() => setLoading(false));
  }, [id]);

  const handleGenerateQuestions = async () => {
    setGenerating(true);
    try {
      await api.generateQuestions(id, undefined, 16);
      alert("Question bank generated and linked to job!");
    } catch (err: any) {
      alert(`Error generating questions: ${err.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleShortlist = async (appId: string) => {
    try {
      await api.shortlistApplication(appId);
      setApplications(prev => prev.map(a =>
        a.id === appId ? { ...a, status: "shortlisted" } : a
      ));
    } catch (err: any) {
      alert(`Error shortlisting: ${err.message}`);
    }
  };

  const handleReject = async (appId: string) => {
    try {
      await api.rejectApplication(appId);
      setApplications(prev => prev.map(a =>
        a.id === appId ? { ...a, status: "rejected" } : a
      ));
    } catch (err: any) {
      alert(`Error rejecting: ${err.message}`);
    }
  };

  const handleCreateInterview = async (appId: string) => {
    try {
      const iv = await api.createInterview(appId);
      await api.sendScheduleInvite(iv.id);
      alert("Interview created and scheduling invite sent!");
      setApplications(prev => prev.map(a =>
        a.id === appId ? { ...a, status: "scheduled" } : a
      ));
    } catch (err: any) {
      alert(`Error creating interview: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!job) {
    return <EmptyState title="Job not found" description="This job may have been removed." />;
  }

  const filtered = applications.filter((a: any) => {
    const q = search.toLowerCase();
    const matchSearch =
      !q ||
      a.candidate?.name?.toLowerCase().includes(q) ||
      a.candidate?.email?.toLowerCase().includes(q);
    const matchStatus = statusFilter === "all" || a.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const counts: Record<string, number> = { all: applications.length };
  applications.forEach((a: any) => {
    counts[a.status] = (counts[a.status] || 0) + 1;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <Link
          href="/admin/jobs"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-text-muted hover:bg-border hover:text-text-primary transition-colors duration-100 mt-1"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold text-text-primary">{job.title}</h1>
          <p className="text-sm text-text-muted mt-0.5">
            {job.department} · {job.location} · {(job.type || "onsite").charAt(0).toUpperCase() + (job.type || "onsite").slice(1)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={handleGenerateQuestions} loading={generating}>
            Generate Questions
          </Button>
          <Badge
            variant={job.status === "published" ? "success" : "outline"}
            className="capitalize"
          >
            {job.status}
          </Badge>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Total", value: applications.length, color: "text-text-primary" },
          { label: "Shortlisted", value: counts.shortlisted || 0, color: "text-brand" },
          { label: "Scheduled", value: counts.scheduled || 0, color: "text-warning" },
          { label: "Completed", value: counts.completed || 0, color: "text-success" },
        ].map((s) => (
          <Card key={s.label}>
            <CardContent className="p-4 text-center">
              <p className={cn("text-2xl font-bold", s.color)}>{s.value}</p>
              <p className="text-xs text-text-muted mt-0.5">{s.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 h-9 flex-1 min-w-[200px] max-w-sm rounded-full border border-border bg-surface px-3 text-sm text-text-muted focus-within:border-brand focus-within:ring-1 focus-within:ring-brand/20 transition-all duration-100">
          <Search className="h-4 w-4 shrink-0" />
          <input
            type="text"
            placeholder="Search candidates..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-muted focus:outline-none"
          />
        </div>

        <div className="flex gap-1.5 flex-wrap">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setStatusFilter(tab.key)}
              className={cn(
                "px-3 py-1.5 rounded-full text-xs font-medium transition-colors duration-100",
                statusFilter === tab.key
                  ? "bg-brand text-white"
                  : "bg-border text-text-muted hover:text-text-primary"
              )}
            >
              {tab.label}{" "}
              {counts[tab.key] !== undefined && (
                <span className="ml-0.5 text-[10px]">({counts[tab.key]})</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Applications table */}
      {filtered.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No applications yet"
          description="Applications will appear here once candidates apply."
        />
      ) : (
        <Card className="overflow-hidden">
          <table className="w-full">
            <thead className="border-b border-border">
              <tr>
                {["Candidate", "Status", "Score", "Applied", "Actions"].map((h) => (
                  <th
                    key={h}
                    className="text-left px-5 py-3 text-xs font-medium text-text-muted uppercase tracking-wide"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.map((a: any) => (
                <tr
                  key={a.id}
                  className="hover:bg-bg transition-colors duration-100"
                >
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2.5">
                      <Avatar size="sm" name={a.candidate?.name || "?"} />
                      <div>
                        <p className="text-sm font-medium text-text-primary">
                          {a.candidate?.name || "Unknown"}
                        </p>
                        <p className="text-xs text-text-muted">
                          {a.candidate?.email || ""}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-3">
                    <StatusBadge status={a.status} />
                  </td>
                  <td className="px-5 py-3">
                    {a.eligibility_score != null && a.eligibility_score > 0 ? (
                      <ScoreBadge score={a.eligibility_score} size="sm" />
                    ) : (
                      <span className="text-xs text-text-muted">—</span>
                    )}
                  </td>
                  <td className="px-5 py-3 text-sm text-text-muted">
                    {a.created_at ? formatDate(a.created_at) : "—"}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      {a.status === "applied" && (
                        <>
                          <Button size="sm" onClick={() => handleShortlist(a.id)}>
                            Shortlist
                          </Button>
                          <Button size="sm" variant="danger" onClick={() => handleReject(a.id)}>
                            Reject
                          </Button>
                        </>
                      )}
                      {a.status === "shortlisted" && (
                        <>
                          <Button size="sm" onClick={() => handleCreateInterview(a.id)}>
                            Invite
                          </Button>
                          <Button size="sm" variant="danger" onClick={() => handleReject(a.id)}>
                            Reject
                          </Button>
                        </>
                      )}
                      {a.status !== "applied" && a.status !== "shortlisted" && (
                        <span className="text-xs text-text-muted">—</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
