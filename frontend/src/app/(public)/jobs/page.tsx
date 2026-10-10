"use client";

import { Suspense, useState, useMemo, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Search, MapPin, Briefcase, Clock } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { adaptJob } from "@/lib/adapters";

// ─── Types ───────────────────────────────────────────────────────────────────

type JobType = "Remote" | "Hybrid" | "Onsite";

const TYPE_BADGE: Record<string, "success" | "default" | "outline"> = {
  Remote: "success",
  remote: "success",
  Hybrid: "default",
  hybrid: "default",
  Onsite: "outline",
  onsite: "outline",
};

const JOB_TYPES: (JobType | "All")[] = ["All", "Remote", "Hybrid", "Onsite"];

// ─── Component ───────────────────────────────────────────────────────────────

function JobsBoard() {
  // White-label widget links here as /jobs?org={org_id} — scope the board
  // to that organization's published jobs.
  const org = useSearchParams().get("org");
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("All Departments");
  const [location, setLocation] = useState("All Locations");
  const [jobType, setJobType] = useState<JobType | "All">("All");

  useEffect(() => {
    api.listJobs({ status: "published", page: 1, page_size: 50, ...(org ? { org } : {}) })
      .then(r => setJobs((r.items || []).map(adaptJob)))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [org]);

  const departments = useMemo(
    () => ["All Departments", ...Array.from(new Set(jobs.map((j: any) => j.department).filter(Boolean)))],
    [jobs]
  );
  const locations = useMemo(
    () => ["All Locations", ...Array.from(new Set(jobs.map((j: any) => j.location).filter(Boolean)))],
    [jobs]
  );

  const filtered = useMemo(() => {
    return jobs.filter((job: any) => {
      const q = search.toLowerCase();
      const matchesSearch =
        !q ||
        job.title?.toLowerCase().includes(q) ||
        (job.required_skills || []).some((s: string) => s.toLowerCase().includes(q)) ||
        job.department?.toLowerCase().includes(q);
      const matchesDept = department === "All Departments" || job.department === department;
      const matchesLoc = location === "All Locations" || job.location === location;
      const matchesType = jobType === "All" || job.type?.toLowerCase() === jobType.toLowerCase();
      return matchesSearch && matchesDept && matchesLoc && matchesType;
    });
  }, [search, department, location, jobType, jobs]);

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-10">
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-10">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-primary">Open Positions</h1>
        <p className="mt-1.5 text-base text-text-muted">
          {jobs.length} roles across engineering, design, and more
        </p>
      </div>

      {/* Filter bar */}
      <div className="mb-8 flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted pointer-events-none" />
            <input
              type="search"
              placeholder="Search by title, skill, or department..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className={cn(
                "h-11 w-full rounded-lg border border-input-border bg-surface pl-9 pr-4 text-sm text-text-primary placeholder:text-text-muted",
                "focus:border-brand focus:ring-2 focus:ring-brand/20 focus:outline-none transition-colors"
              )}
            />
          </div>

          {/* Department */}
          <select
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            className={cn(
              "h-11 rounded-lg border border-input-border bg-surface px-3.5 text-sm text-text-primary",
              "focus:border-brand focus:ring-2 focus:ring-brand/20 focus:outline-none transition-colors",
              "sm:w-52"
            )}
          >
            {departments.map((d) => <option key={d}>{d}</option>)}
          </select>

          {/* Location */}
          <select
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className={cn(
              "h-11 rounded-lg border border-input-border bg-surface px-3.5 text-sm text-text-primary",
              "focus:border-brand focus:ring-2 focus:ring-brand/20 focus:outline-none transition-colors",
              "sm:w-48"
            )}
          >
            {locations.map((l) => <option key={l}>{l}</option>)}
          </select>
        </div>

        {/* Job type pills */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-text-muted font-medium">Type:</span>
          {JOB_TYPES.map((t) => (
            <button
              key={t}
              onClick={() => setJobType(t)}
              className={cn(
                "rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors duration-100",
                jobType === t
                  ? "bg-brand text-white"
                  : "bg-surface border border-border text-text-muted hover:text-text-primary hover:border-brand/40"
              )}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Results count */}
      {search || department !== "All Departments" || location !== "All Locations" || jobType !== "All" ? (
        <p className="mb-5 text-sm text-text-muted">
          Showing <span className="font-semibold text-text-primary">{filtered.length}</span> result{filtered.length !== 1 ? "s" : ""}
        </p>
      ) : null}

      {/* Job grid */}
      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-brand-light">
            <Briefcase className="h-7 w-7 text-brand" />
          </div>
          <h3 className="text-lg font-semibold text-text-primary">No positions found</h3>
          <p className="mt-1 text-sm text-text-muted max-w-sm">
            Try adjusting your search or filters to find matching roles.
          </p>
          <Button
            variant="secondary"
            size="sm"
            className="mt-5"
            onClick={() => {
              setSearch("");
              setDepartment("All Departments");
              setLocation("All Locations");
              setJobType("All");
            }}
          >
            Clear filters
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((job: any) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      )}
    </div>
  );
}

// useSearchParams requires a Suspense boundary for prerendering.
export default function JobsPage() {
  return (
    <Suspense fallback={null}>
      <JobsBoard />
    </Suspense>
  );
}

// ─── Job Card ─────────────────────────────────────────────────────────────────

function JobCard({ job }: { job: any }) {
  const skills = job.required_skills || [];
  const visibleSkills = skills.slice(0, 4);
  const extraCount = skills.length - visibleSkills.length;
  const typeLabel = (job.type || "onsite").charAt(0).toUpperCase() + (job.type || "onsite").slice(1);
  const daysAgo = job.created_at
    ? Math.max(0, Math.floor((Date.now() - new Date(job.created_at).getTime()) / 86400000))
    : 0;

  return (
    <Card className="flex flex-col hover:border-brand/40 transition-colors duration-150">
      <CardContent className="flex flex-1 flex-col gap-4 p-5">
        {/* Top row */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h2 className="text-base font-semibold text-text-primary leading-snug">
              {job.title}
            </h2>
            <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-text-muted">
              <span>{job.department}</span>
              <span className="text-border">·</span>
              <span className="flex items-center gap-0.5">
                <MapPin className="h-3 w-3" />
                {job.location}
              </span>
            </div>
          </div>
          <Badge variant={TYPE_BADGE[job.type] || "outline"} className="shrink-0">
            {typeLabel}
          </Badge>
        </div>

        {/* Skills */}
        <div className="flex flex-wrap gap-1.5">
          {visibleSkills.map((skill: string) => (
            <Badge key={skill} variant="outline" className="text-xs">
              {skill}
            </Badge>
          ))}
          {extraCount > 0 && (
            <Badge variant="outline" className="text-xs text-text-muted">
              +{extraCount} more
            </Badge>
          )}
        </div>

        {/* Footer */}
        <div className="mt-auto flex items-center justify-between pt-3 border-t border-border">
          <div>
            {(job.salary_min > 0 || job.salary_max > 0) && (
              <p className="text-sm font-semibold text-text-primary">
                ₹{(job.salary_min / 100000).toFixed(0)}–{(job.salary_max / 100000).toFixed(0)} LPA
              </p>
            )}
            <p className="text-xs text-text-muted flex items-center gap-1 mt-0.5">
              <Clock className="h-3 w-3" />
              Posted {daysAgo === 0 ? "today" : daysAgo === 1 ? "1 day ago" : `${daysAgo} days ago`}
            </p>
          </div>
          <Button asChild size="sm">
            <Link href={`/jobs/${job.id}/apply`}>Apply Now</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
