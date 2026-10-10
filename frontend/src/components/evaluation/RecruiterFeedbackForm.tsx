"use client";

import { useState } from "react";
import { ThumbsUp, ThumbsDown, Minus, CheckCircle2, Star } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

interface Props {
  interviewId: string;
}

type Decision = "hire" | "maybe" | "no_hire";

const DECISIONS: { value: Decision; label: string; icon: typeof ThumbsUp }[] = [
  { value: "hire", label: "Hire", icon: ThumbsUp },
  { value: "maybe", label: "Maybe", icon: Minus },
  { value: "no_hire", label: "No Hire", icon: ThumbsDown },
];

export default function RecruiterFeedbackForm({ interviewId }: Props) {
  const [decision, setDecision] = useState<Decision | null>(null);
  const [score, setScore] = useState("");
  const [rating, setRating] = useState(0);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!decision) {
      setError("Please select a decision.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const scoreNum = score.trim() === "" ? undefined : Number(score);
      const res: any = await api.submitFeedback({
        interview_id: interviewId,
        recruiter_decision: decision,
        recruiter_score:
          scoreNum != null && isFinite(scoreNum) ? scoreNum : undefined,
        rating: rating > 0 ? rating : undefined,
        notes: notes.trim() || undefined,
      });
      if (res?.ok === false) {
        setError(res?.reason ?? res?.message ?? "Failed to submit feedback.");
      } else {
        setSuccess(true);
      }
    } catch (e: any) {
      setError(e?.message ?? "Failed to submit feedback.");
    } finally {
      setSubmitting(false);
    }
  };

  const reset = () => {
    setDecision(null);
    setScore("");
    setRating(0);
    setNotes("");
    setSuccess(false);
    setError(null);
  };

  if (success) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-success-light">
            <CheckCircle2 className="h-7 w-7 text-success" />
          </div>
          <div>
            <p className="text-base font-semibold text-text-primary">Feedback submitted</p>
            <p className="mt-1 text-sm text-text-muted">
              Your decision feeds the continuous learning model and improves future scoring.
            </p>
          </div>
          <Button variant="secondary" onClick={reset}>
            Submit another
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recruiter Feedback</CardTitle>
        <CardDescription>
          Record your decision. This feeds the continuous learning model.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        {/* Decision buttons */}
        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium text-text-primary">Decision</span>
          <div className="flex flex-wrap gap-2">
            {DECISIONS.map(({ value, label, icon: Icon }) => {
              const active = decision === value;
              return (
                <button
                  key={value}
                  type="button"
                  onClick={() => setDecision(value)}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-colors",
                    active
                      ? "border-brand bg-brand-light text-brand"
                      : "border-border text-text-muted hover:text-text-primary"
                  )}
                  aria-pressed={active}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Score */}
        <Input
          label="Score (0–100, optional)"
          type="number"
          min={0}
          max={100}
          value={score}
          onChange={(e) => setScore(e.target.value)}
          placeholder="e.g. 78"
        />

        {/* Rating */}
        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-text-primary">Rating (optional)</span>
          <div className="flex items-center gap-1">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setRating(rating === n ? 0 : n)}
                aria-label={`${n} star${n > 1 ? "s" : ""}`}
                className="p-0.5"
              >
                <Star
                  className={cn(
                    "h-6 w-6 transition-colors",
                    n <= rating ? "fill-warning text-warning" : "text-border"
                  )}
                />
              </button>
            ))}
          </div>
        </div>

        {/* Notes */}
        <Textarea
          label="Notes (optional)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Additional context for this decision…"
        />

        {error && <p className="text-sm text-error">{error}</p>}

        <div>
          <Button onClick={submit} loading={submitting} disabled={submitting || !decision}>
            Submit Feedback
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
