"use client";

import { useState, useMemo, useEffect, use } from "react";
import Link from "next/link";
import {
  Clock,
  Calendar,
  Video,
  Layers,
  Download,
  CheckCircle2,
  Info,
  Wifi,
  Mic,
  Monitor,
  AlertCircle
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn, formatDate } from "@/lib/utils";
import { api } from "@/lib/api";

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_LABELS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function formatShortDate(date: Date) {
  return `${MONTH_LABELS[date.getMonth()]} ${date.getDate()}`;
}

function formatFullDate(date: Date) {
  return `${DAY_LABELS[date.getDay()]}, ${MONTH_LABELS[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}`;
}

export default function SchedulePage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = use(params);
  const [info, setInfo] = useState<any>(null);
  const [selectedDayStr, setSelectedDayStr] = useState<string | null>(null);
  const [selectedSlotId, setSelectedSlotId] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [booking, setBooking] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getScheduleInfo(token)
      .then((data) => {
        setInfo(data);
      })
      .catch((err) => {
        console.error("Schedule info error:", err);
        setError("Invalid or expired scheduling token.");
      })
      .finally(() => setLoading(false));
  }, [token]);

  const slotsGroupedByDay = useMemo(() => {
    if (!info?.available_slots) return {};
    const groups: Record<string, any[]> = {};
    info.available_slots.forEach((slot: any) => {
      const d = new Date(slot.slot_datetime);
      const dateStr = d.toDateString();
      if (!groups[dateStr]) groups[dateStr] = [];
      groups[dateStr].push(slot);
    });
    return groups;
  }, [info]);

  const days = useMemo(() => {
    return Object.keys(slotsGroupedByDay).map((dateStr) => new Date(dateStr));
  }, [slotsGroupedByDay]);

  const slotsForSelectedDay = useMemo(() => {
    if (!selectedDayStr) return [];
    return slotsGroupedByDay[selectedDayStr] || [];
  }, [selectedDayStr, slotsGroupedByDay]);

  const selectedSlotDetail = useMemo(() => {
    if (!selectedSlotId || !info?.available_slots) return null;
    return info.available_slots.find((s: any) => s.id === selectedSlotId);
  }, [selectedSlotId, info]);

  const handleDaySelect = (day: Date) => {
    setSelectedDayStr(day.toDateString());
    setSelectedSlotId(null);
  };

  const handleConfirm = async () => {
    if (!selectedSlotId) return;
    setBooking(true);
    setError("");
    try {
      await api.bookSlot(token, selectedSlotId);
      setConfirmed(true);
    } catch (err: any) {
      setError(err.message || "Failed to book interview slot.");
    } finally {
      setBooking(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error && !confirmed) {
    return (
      <div className="max-w-md mx-auto text-center py-12">
        <AlertCircle className="h-12 w-12 text-error mx-auto mb-4" />
        <h1 className="text-xl font-bold text-text-primary mb-2">Scheduling Unavailable</h1>
        <p className="text-sm text-text-muted mb-6">{error}</p>
        <Button asChild size="sm">
          <Link href="/jobs">Browse Jobs</Link>
        </Button>
      </div>
    );
  }

  if (confirmed && selectedSlotDetail) {
    const slotDate = new Date(selectedSlotDetail.slot_datetime);
    const timeStr = slotDate.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });

    return (
      <div className="max-w-lg mx-auto text-center py-12">
        <div className="flex justify-center mb-6">
          <div className="h-20 w-20 rounded-full bg-success-light flex items-center justify-center">
            <CheckCircle2 className="h-10 w-10 text-success" />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-text-primary mb-2">
          Interview Confirmed!
        </h1>
        <p className="text-text-muted mb-6">
          Your interview for{" "}
          <span className="font-semibold text-text-primary">{info.job_title}</span>{" "}
          is scheduled.
        </p>

        <Card className="mb-6 text-left">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center gap-3">
              <Calendar className="h-4 w-4 text-brand shrink-0" />
              <span className="text-sm font-medium text-text-primary">
                {formatFullDate(slotDate)}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <Clock className="h-4 w-4 text-brand shrink-0" />
              <span className="text-sm font-medium text-text-primary">
                {timeStr} · {selectedSlotDetail.duration_minutes || 60} minutes
              </span>
            </div>
            <div className="flex items-center gap-3">
              <Video className="h-4 w-4 text-brand shrink-0" />
              <span className="text-sm text-text-muted">AI Voice Interview Room</span>
            </div>
          </CardContent>
        </Card>

        <p className="text-xs text-text-muted mb-6">
          A confirmation email with your interview link has been sent to your inbox.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button asChild>
            <Link href={`/portal?token=${token}`}>Back to Portal</Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary">
          Schedule Your Interview
        </h1>
        <p className="text-sm text-text-muted mt-1">
          Select a date and time that works best for you
        </p>
      </div>

      {/* Job info */}
      <Card className="mb-6">
        <CardContent className="p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold text-text-primary">
                {info.job_title}
              </h2>
              <p className="text-sm text-text-muted mt-0.5">
                NexusAI Hiring Platform
              </p>
            </div>
            <div className="flex flex-col items-end gap-1.5 shrink-0">
              <div className="flex items-center gap-1.5 text-xs text-text-muted">
                <Clock className="h-3.5 w-3.5" />
                Multi-round Interview
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="mb-4 rounded-lg bg-error-light border border-error/20 px-4 py-3">
          <p className="text-sm text-error font-medium">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
        {/* Left: Calendar + slots */}
        <div className="lg:col-span-3 space-y-5">
          {/* Calendar */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-brand" />
                Select a Date
              </CardTitle>
            </CardHeader>
            <CardContent>
              {days.length === 0 ? (
                <p className="text-sm text-text-muted text-center py-4">
                  No available dates. Please contact the hiring team to open scheduling slots.
                </p>
              ) : (
                <div className="grid grid-cols-5 gap-2">
                  {days.map((day, i) => {
                    const isSelected = selectedDayStr === day.toDateString();

                    return (
                      <button
                        key={i}
                        type="button"
                        onClick={() => handleDaySelect(day)}
                        className={cn(
                          "flex flex-col items-center p-2.5 rounded-lg border text-center transition-all",
                          isSelected
                            ? "border-brand bg-brand text-white"
                            : "border-border bg-surface hover:border-brand/40 hover:bg-brand-light/40"
                        )}
                      >
                        <span
                          className={cn(
                            "text-[10px] font-medium",
                            isSelected ? "text-white/80" : "text-text-muted"
                          )}
                        >
                          {DAY_LABELS[day.getDay()]}
                        </span>
                        <span
                          className={cn(
                            "text-sm font-semibold mt-0.5",
                            isSelected ? "text-white" : "text-text-primary"
                          )}
                        >
                          {day.getDate()}
                        </span>
                        <span
                          className={cn(
                            "text-[9px] mt-0.5",
                            isSelected ? "text-white/70" : "text-text-muted"
                          )}
                        >
                          {MONTH_LABELS[day.getMonth()]}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Time slots */}
          {selectedDayStr && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-brand" />
                  Available Times — {formatShortDate(new Date(selectedDayStr))}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                  {slotsForSelectedDay.map((slot) => {
                    const selected = selectedSlotId === slot.id;
                    const slotTime = new Date(slot.slot_datetime).toLocaleTimeString("en-US", {
                      hour: "numeric",
                      minute: "2-digit",
                      hour12: true,
                    });

                    return (
                      <button
                        key={slot.id}
                        type="button"
                        onClick={() => setSelectedSlotId(slot.id)}
                        className={cn(
                          "px-3 py-2.5 rounded-lg border text-sm font-medium transition-all",
                          selected
                            ? "border-brand bg-brand text-white"
                            : "border-border bg-surface hover:border-brand/50 hover:bg-brand-light/30 text-text-primary"
                        )}
                      >
                        {slotTime}
                      </button>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right: Summary + instructions */}
        <div className="lg:col-span-2 space-y-4">
          {/* Selected summary */}
          {selectedDayStr && selectedSlotDetail ? (
            <Card className="border-brand/30 bg-brand-light/20">
              <CardContent className="p-5 space-y-3">
                <h3 className="text-sm font-semibold text-brand flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  Your Selection
                </h3>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm text-text-primary">
                    <Calendar className="h-3.5 w-3.5 text-text-muted" />
                    {formatFullDate(new Date(selectedDayStr))}
                  </div>
                  <div className="flex items-center gap-2 text-sm text-text-primary">
                    <Clock className="h-3.5 w-3.5 text-text-muted" />
                    {new Date(selectedSlotDetail.slot_datetime).toLocaleTimeString("en-US", {
                      hour: "numeric",
                      minute: "2-digit",
                      hour12: true,
                    })} · {selectedSlotDetail.duration_minutes || 60} minutes
                  </div>
                  <div className="flex items-center gap-2 text-sm text-text-primary">
                    <Video className="h-3.5 w-3.5 text-text-muted" />
                    AI Voice Interview
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-dashed">
              <CardContent className="p-5 text-center">
                <Calendar className="h-8 w-8 text-text-muted/40 mx-auto mb-2" />
                <p className="text-sm text-text-muted">
                  Select a date and time to continue
                </p>
              </CardContent>
            </Card>
          )}

          {/* Instructions */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <Info className="h-4 w-4 text-brand" />
                Before Your Interview
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-3">
              <ul className="space-y-2.5">
                {[
                  { icon: Video, text: "Ensure you have a working microphone and speakers" },
                  { icon: Monitor, text: "Choose a quiet environment for clear speech capture" },
                  { icon: Wifi, text: "Stable internet connection is required" },
                  { icon: Mic, text: "Speak naturally, wait for AI to finish speaking" },
                  { icon: Clock, text: "The voice loop adapts to your answers" },
                ].map((item, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-xs text-text-muted">
                    <item.icon className="h-3.5 w-3.5 text-brand shrink-0 mt-0.5" />
                    {item.text}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {/* Confirm button */}
          <Button
            className="w-full"
            size="lg"
            disabled={!selectedDayStr || !selectedSlotId}
            loading={booking}
            onClick={handleConfirm}
          >
            Confirm Schedule
          </Button>
        </div>
      </div>
    </div>
  );
}
