"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, Search, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { cn, formatDate } from "@/lib/utils";
import { api } from "@/lib/api";
import { adaptJob } from "@/lib/adapters";
import type { JobStatus } from "@/types";

const STATUS_CONFIG: Record<
  JobStatus,
  { label: string; variant: "success" | "default" | "outline" | "error" }
> = {
  published: { label: "Published", variant: "success" },
  draft: { label: "Draft", variant: "outline" },
  closed: { label: "Closed", variant: "default" },
  archived: { label: "Archived", variant: "error" },
};

type StatusFilter = JobStatus | "all";

export default function JobsPage() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<StatusFilter>("all");

  useEffect(() => {
    api.listJobs({ page: 1, page_size: 100 })
      .then(r => setJobs((r.items || []).map(adaptJob)))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const filtered = jobs.filter((j: any) => {
    const q = search.toLowerCase();
    const matchSearch =
      !q ||
      j.title?.toLowerCase().includes(q) ||
      j.department?.toLowerCase().includes(q);
    const matchStatus = status === "all" || j.status === status;
    return matchSearch && matchStatus;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Jobs</h1>
          <p className="text-sm text-text-muted mt-0.5">
            {jobs.length} job postings
          </p>
        </div>
        <Button asChild size="sm">
          <Link href="/admin/jobs/new">
            <Plus className="h-4 w-4" />
            New Job
          </Link>
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 h-9 flex-1 min-w-[200px] max-w-sm rounded-full border border-border bg-surface px-3 text-sm text-text-muted focus-within:border-brand focus-within:ring-1 focus-within:ring-brand/20 transition-all duration-100">
          <Search className="h-4 w-4 shrink-0" />
          <input
            type="text"
            placeholder="Search jobs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-muted focus:outline-none"
          />
        </div>

        <select
          value={status}
          onChange={(e) => setStatus(e.target.value as StatusFilter)}
          className="h-9 rounded-lg border border-border bg-surface px-3 text-sm text-text-muted focus:border-brand focus:outline-none"
        >
          <option value="all">All Statuses</option>
          <option value="published">Published</option>
          <option value="draft">Draft</option>
          <option value="closed">Closed</option>
          <option value="archived">Archived</option>
        </select>
      </div>

      {/* Jobs list */}
      {filtered.length === 0 ? (
        <EmptyState
          title="No jobs found"
          description={search ? "Try adjusting your search." : "Create your first job posting."}
          action={
            !search ? (
              <Button asChild size="sm">
                <Link href="/admin/jobs/new">
                  <Plus className="h-4 w-4" />
                  Create Job
                </Link>
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="space-y-3">
          {filtered.map((job: any) => {
            const sc = STATUS_CONFIG[job.status as JobStatus] ?? STATUS_CONFIG.draft;
            return (
              <Link key={job.id} href={`/admin/jobs/${job.id}`}>
                <Card className="hover:border-brand/40 transition-colors duration-100 cursor-pointer">
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h2 className="text-base font-semibold text-text-primary truncate">
                            {job.title}
                          </h2>
                          <Badge variant={sc.variant} className="shrink-0">
                            {sc.label}
                          </Badge>
                        </div>
                        <p className="text-sm text-text-muted">
                          {job.department} · {job.location} · {(job.type || "onsite").charAt(0).toUpperCase() + (job.type || "onsite").slice(1)}
                        </p>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-sm font-semibold text-text-primary">
                          {job.applications_count ?? 0}
                        </p>
                        <p className="text-xs text-text-muted">Applications</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 mt-3 pt-3 border-t border-border">
                      <span className="text-xs text-text-muted">
                        Created {job.created_at ? formatDate(job.created_at) : "—"}
                      </span>
                      {job.required_skills?.slice(0, 3).map((s: string) => (
                        <Badge key={s} variant="outline" className="text-xs">
                          {s}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
