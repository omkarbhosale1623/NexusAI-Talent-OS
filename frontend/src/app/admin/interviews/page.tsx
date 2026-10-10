"use client";

import { useState } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight, List, Calendar } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar } from "@/components/ui/avatar";
import { StatusBadge } from "@/components/ui/status-badge";
import { cn, formatDate } from "@/lib/utils";
import type { InterviewStatus } from "@/types";

interface InterviewItem {
  id: string;
  candidate: string;
  job: string;
  date: string; // ISO
  time: string; // "10:00"
  duration: number;
  status: InterviewStatus;
  dayOfWeek: number; // 0=Sun
  hour: number;
}

// Week of Mar 10–16, 2026
const INTERVIEWS: InterviewItem[] = [
  { id: "1", candidate: "Priya Sharma", job: "Senior Frontend Engineer", date: "2026-03-10", time: "10:00", duration: 52, status: "completed", dayOfWeek: 1, hour: 10 },
  { id: "2", candidate: "Vikram Singh", job: "Backend Engineer", date: "2026-03-11", time: "14:00", duration: 48, status: "completed", dayOfWeek: 2, hour: 14 },
  { id: "3", candidate: "Ananya Mehta", job: "Product Manager", date: "2026-03-14", time: "11:00", duration: 55, status: "in_progress", dayOfWeek: 5, hour: 11 },
  { id: "4", candidate: "Arjun Nair", job: "Senior Frontend Engineer", date: "2026-03-15", time: "15:00", duration: 52, status: "scheduled", dayOfWeek: 6, hour: 15 },
  { id: "5", candidate: "Meera Iyer", job: "Data Scientist", date: "2026-03-12", time: "16:00", duration: 50, status: "completed", dayOfWeek: 3, hour: 16 },
  { id: "6", candidate: "Rohan Gupta", job: "ML Engineer", date: "2026-03-13", time: "10:00", duration: 48, status: "completed", dayOfWeek: 4, hour: 10 },
  { id: "7", candidate: "Siddharth Rao", job: "Backend Engineer", date: "2026-03-16", time: "13:00", duration: 52, status: "scheduled", dayOfWeek: 0, hour: 13 },
];

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const HOURS = [9, 10, 11, 12, 13, 14, 15, 16, 17];

const STATUS_COLORS: Record<InterviewStatus, string> = {
  scheduled: "bg-brand-light border-brand text-brand",
  in_progress: "bg-warning-light border-warning text-warning",
  completed: "bg-success-light border-success text-success",
  cancelled: "bg-error-light border-error text-error",
};

type ViewMode = "calendar" | "list";

export default function InterviewsPage() {
  const [viewMode, setViewMode] = useState<ViewMode>("calendar");
  const [weekOffset, setWeekOffset] = useState(0); // 0 = current week Mar 10-16

  const WEEK_LABEL = weekOffset === 0
    ? "Mar 10 – 16, 2026"
    : weekOffset === 1
    ? "Mar 17 – 23, 2026"
    : "Mar 3 – 9, 2026";

  const weekDates = ["Mar 10", "Mar 11", "Mar 12", "Mar 13", "Mar 14", "Mar 15", "Mar 16"];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Interviews</h1>
          <p className="text-sm text-text-muted mt-0.5">
            {INTERVIEWS.length} interviews this week.
          </p>
        </div>
        {/* View toggle */}
        <div className="flex rounded-lg border border-border overflow-hidden">
          <button
            onClick={() => setViewMode("calendar")}
            className={cn(
              "flex items-center gap-1.5 px-3 h-9 text-sm font-medium transition-colors duration-100",
              viewMode === "calendar" ? "bg-brand text-white" : "text-text-muted hover:bg-bg"
            )}
          >
            <Calendar className="h-4 w-4" />
            <span className="hidden sm:inline">Calendar</span>
          </button>
          <button
            onClick={() => setViewMode("list")}
            className={cn(
              "flex items-center gap-1.5 px-3 h-9 text-sm font-medium transition-colors duration-100",
              viewMode === "list" ? "bg-brand text-white" : "text-text-muted hover:bg-bg"
            )}
          >
            <List className="h-4 w-4" />
            <span className="hidden sm:inline">List</span>
          </button>
        </div>
      </div>

      {/* Week navigation */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setWeekOffset((w) => w - 1)}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-border text-text-muted hover:bg-border transition-colors duration-100"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="text-sm font-semibold text-text-primary min-w-[160px] text-center">
          {WEEK_LABEL}
        </span>
        <button
          onClick={() => setWeekOffset((w) => w + 1)}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-border text-text-muted hover:bg-border transition-colors duration-100"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
        <button
          onClick={() => setWeekOffset(0)}
          className="ml-1 px-3 h-8 text-xs font-medium text-brand border border-brand rounded-full hover:bg-brand-light transition-colors duration-100"
        >
          Today
        </button>
      </div>

      {viewMode === "calendar" ? (
        /* ── CALENDAR VIEW ── */
        <Card className="overflow-hidden">
          {/* Day headers */}
          <div className="grid grid-cols-8 border-b border-border">
            <div className="p-3 text-xs text-text-muted" /> {/* time column */}
            {DAYS.map((d, i) => (
              <div key={d} className="p-3 text-center border-l border-border">
                <p className="text-xs font-medium text-text-muted">{d}</p>
                <p className="text-xs text-text-muted mt-0.5">{weekDates[i]}</p>
              </div>
            ))}
          </div>

          {/* Time grid */}
          <div className="overflow-y-auto max-h-[520px]">
            {HOURS.map((hour) => (
              <div key={hour} className="grid grid-cols-8 border-b border-border min-h-[72px]">
                {/* Time label */}
                <div className="p-2 text-right pr-3 pt-2">
                  <span className="text-xs text-text-muted tabular-nums">
                    {hour > 12 ? `${hour - 12}:00 PM` : `${hour}:00 AM`}
                  </span>
                </div>
                {/* Day cells */}
                {DAYS.map((_, dayIdx) => {
                  const interview = INTERVIEWS.find(
                    (iv) => iv.dayOfWeek === dayIdx && iv.hour === hour
                  );
                  return (
                    <div
                      key={dayIdx}
                      className="p-1 border-l border-border min-h-[72px]"
                    >
                      {interview && (
                        <Link href={`/admin/candidates/${interview.id}`}>
                          <div
                            className={cn(
                              "rounded-md border p-2 text-xs cursor-pointer hover:opacity-80 transition-opacity duration-100",
                              STATUS_COLORS[interview.status]
                            )}
                          >
                            <p className="font-semibold truncate">
                              {interview.candidate}
                            </p>
                            <p className="truncate opacity-80 mt-0.5">
                              {interview.job}
                            </p>
                            <p className="mt-1 opacity-70">
                              {interview.time} · {interview.duration}m
                            </p>
                          </div>
                        </Link>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </Card>
      ) : (
        /* ── LIST VIEW ── */
        <div className="space-y-3">
          {INTERVIEWS.map((iv) => (
            <Card key={iv.id} className="p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <Avatar size="sm" name={iv.candidate} />
                  <div>
                    <p className="text-sm font-semibold text-text-primary">
                      {iv.candidate}
                    </p>
                    <p className="text-xs text-text-muted mt-0.5">{iv.job}</p>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <div className="text-right">
                    <p className="text-sm text-text-primary">
                      {formatDate(iv.date)}
                    </p>
                    <p className="text-xs text-text-muted">
                      {iv.time} · {iv.duration} min
                    </p>
                  </div>
                  <StatusBadge status={iv.status} />
                  <Link
                    href={`/admin/candidates/${iv.id}`}
                    className="text-xs text-brand hover:text-brand-hover font-medium"
                  >
                    View
                  </Link>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-4 pt-2">
        {(["scheduled", "in_progress", "completed", "cancelled"] as InterviewStatus[]).map((s) => (
          <div key={s} className="flex items-center gap-1.5">
            <div className={cn("h-3 w-3 rounded border", STATUS_COLORS[s])} />
            <StatusBadge status={s} />
          </div>
        ))}
      </div>
    </div>
  );
}
