"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Briefcase,
  Users,
  Video,
  TrendingUp,
  ArrowUpRight,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Avatar } from "@/components/ui/avatar";
import { ScoreBadge } from "@/components/ui/score-badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { Progress } from "@/components/ui/progress";
import { formatDate } from "@/lib/utils";
import { api } from "@/lib/api";
import { adaptDashboardStats } from "@/lib/adapters";
import { useAuth } from "@/hooks/useAuth";

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<any>(null);
  const [recentInterviews, setRecentInterviews] = useState<any[]>([]);
  const [pipeline, setPipeline] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.dashboard(),
      api.listInterviews({ status: "completed", page: 1, page_size: 5 }),
    ]).then(([dash, ivs]) => {
      const adapted = adaptDashboardStats(dash);
      setStats(adapted);
      setRecentInterviews(ivs.items || []);

      const p = dash.pipeline || {};
      const total = p.total_applications || 1;
      setPipeline([
        { label: "Applied", count: p.total_applications ?? 0, total, color: "bg-text-muted" },
        { label: "Shortlisted", count: p.shortlisted ?? 0, total, color: "bg-brand" },
        { label: "Scheduled", count: p.interview_scheduled ?? 0, total, color: "bg-warning" },
        { label: "Interviewed", count: p.interview_completed ?? 0, total, color: "bg-brand" },
        { label: "Hired", count: p.hired ?? 0, total, color: "bg-success" },
      ]);
    }).catch(console.error)
    .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const STATS = [
    {
      label: "Active Jobs",
      value: String(stats?.active_jobs ?? 0),
      trend: `${stats?.active_jobs ?? 0} total`,
      icon: Briefcase,
      iconBg: "bg-brand-light",
      iconColor: "text-brand",
    },
    {
      label: "Total Candidates",
      value: String(stats?.total_candidates ?? 0),
      trend: "across all jobs",
      icon: Users,
      iconBg: "bg-success-light",
      iconColor: "text-success",
    },
    {
      label: "Interviews This Week",
      value: String(stats?.interviews_this_week ?? 0),
      trend: `${stats?.total_interviews ?? 0} total`,
      icon: Video,
      iconBg: "bg-warning-light",
      iconColor: "text-warning",
    },
    {
      label: "Average Score",
      value: `${Math.round(stats?.avg_score ?? 0)}/100`,
      trend: `${Math.round(stats?.pass_rate ?? 0)}% hire rate`,
      icon: TrendingUp,
      iconBg: "bg-brand-light",
      iconColor: "text-brand",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Dashboard</h1>
          <p className="text-sm text-text-muted mt-0.5">
            Welcome back, {user?.full_name || "there"}. Here&apos;s what&apos;s happening.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button asChild variant="secondary" size="sm">
            <Link href="/admin/candidates">View Candidates</Link>
          </Button>
          <Button asChild size="sm">
            <Link href="/admin/jobs/new">Post New Job</Link>
          </Button>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {STATS.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-text-muted">{stat.label}</p>
                    <p className="text-2xl font-bold text-text-primary mt-1">
                      {stat.value}
                    </p>
                    <p className="text-xs text-text-muted mt-1 flex items-center gap-1">
                      <ArrowUpRight className="h-3 w-3 text-success" />
                      {stat.trend}
                    </p>
                  </div>
                  <div
                    className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${stat.iconBg}`}
                  >
                    <Icon className={`h-5 w-5 ${stat.iconColor}`} />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Recent Activity table */}
        <Card className="xl:col-span-2">
          <CardHeader className="p-5 pb-4">
            <div className="flex items-center justify-between">
              <CardTitle>Recent Interviews</CardTitle>
              <Link
                href="/admin/interviews"
                className="text-sm text-brand hover:text-brand-hover font-medium"
              >
                View all
              </Link>
            </div>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-t border-border">
                  <th className="text-left px-5 py-3 text-xs font-medium text-text-muted uppercase tracking-wide">
                    Candidate
                  </th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-text-muted uppercase tracking-wide hidden sm:table-cell">
                    Job Title
                  </th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-text-muted uppercase tracking-wide">
                    Status
                  </th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-text-muted uppercase tracking-wide">
                    Score
                  </th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-text-muted uppercase tracking-wide hidden md:table-cell">
                    Date
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {recentInterviews.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-5 py-8 text-center text-sm text-text-muted">
                      No completed interviews yet
                    </td>
                  </tr>
                ) : (
                  recentInterviews.map((row: any) => (
                    <tr
                      key={row.id}
                      className="hover:bg-bg transition-colors duration-100"
                    >
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2.5">
                          <Avatar size="sm" name={row.candidate_name || row.id?.slice(0, 8)} />
                          <span className="text-sm font-medium text-text-primary whitespace-nowrap">
                            {row.candidate_name || `Interview ${row.id?.slice(0, 8)}`}
                          </span>
                        </div>
                      </td>
                      <td className="px-5 py-3 hidden sm:table-cell">
                        <span className="text-sm text-text-muted whitespace-nowrap">
                          {row.job_title || "—"}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        <StatusBadge status={row.status} />
                      </td>
                      <td className="px-5 py-3">
                        {row.overall_score > 0 ? (
                          <ScoreBadge score={row.overall_score} size="sm" />
                        ) : (
                          <span className="text-xs text-text-muted">—</span>
                        )}
                      </td>
                      <td className="px-5 py-3 hidden md:table-cell">
                        <span className="text-sm text-text-muted">
                          {row.created_at ? formatDate(row.created_at) : "—"}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Pipeline summary */}
        <Card>
          <CardHeader className="p-5 pb-4">
            <CardTitle>Hiring Pipeline</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 space-y-4">
            {pipeline.map((stage) => (
              <div key={stage.label}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm text-text-primary">
                    {stage.label}
                  </span>
                  <span className="text-sm font-semibold text-text-primary tabular-nums">
                    {stage.count}
                  </span>
                </div>
                <Progress
                  value={stage.total > 0 ? (stage.count / stage.total) * 100 : 0}
                />
              </div>
            ))}
            <div className="pt-2 border-t border-border">
              <p className="text-xs text-text-muted">
                {pipeline[0]?.count ?? 0} total applications
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
