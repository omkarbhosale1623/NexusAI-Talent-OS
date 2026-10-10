"use client";

import { useState, useEffect, useRef, useCallback, use, useMemo } from "react";
import Link from "next/link";
import {
  Mic,
  MicOff,
  Camera,
  CameraOff,
  PhoneOff,
  ChevronRight,
  User,
  Waves,
  Circle,
  Clock,
  MessageSquare,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useSpeech } from "@/hooks/useSpeech";
import { useFaceDetection } from "@/hooks/useFaceDetection";
import { api } from "@/lib/api";

// ─── Types ───────────────────────────────────────────────────────────────────

interface Round {
  id: number;
  name: string;
  type: string;
  totalQuestions: number;
}

interface TranscriptEntry {
  speaker: "AI" | "You";
  text: string;
  timestamp: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const ROUNDS: Round[] = [
  { id: 1, name: "Introduction", type: "intro", totalQuestions: 3 },
  { id: 2, name: "Technical", type: "technical", totalQuestions: 5 },
  { id: 3, name: "Behavioral", type: "behavioral", totalQuestions: 4 },
  { id: 4, name: "HR & Culture", type: "hr", totalQuestions: 3 },
];

const ROUND_COLORS: Record<number, string> = {
  1: "bg-brand-light text-brand",
  2: "bg-warning-light text-warning",
  3: "bg-success-light text-success",
  4: "bg-border text-text-muted",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatSeconds(s: number) {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

function now() {
  const d = new Date();
  return `${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function AIAvatar({ isSpeaking }: { isSpeaking: boolean }) {
  return (
    <div className="relative h-full w-full">
      {isSpeaking && (
        <span className="absolute inset-0 rounded-full bg-brand/30 animate-ping" />
      )}
      <div
        className={cn(
          "relative h-full w-full rounded-full flex items-center justify-center",
          "bg-gradient-to-br from-brand to-blue-800"
        )}
      >
        <Waves className="h-5 w-5 text-white" />
      </div>
    </div>
  );
}

function TranscriptPanel({ entries }: { entries: TranscriptEntry[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-white/10 shrink-0">
        <MessageSquare className="h-4 w-4 text-white/60" />
        <span className="text-sm font-medium text-white/80">Transcript</span>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin">
        {entries.length === 0 ? (
          <p className="text-xs text-white/30 text-center py-4">No transcription entries yet.</p>
        ) : (
          entries.map((entry, i) => (
            <div key={i} className="space-y-1">
              <div className="flex items-center gap-1.5">
                <span
                  className={cn(
                    "text-[10px] font-semibold uppercase tracking-wide",
                    entry.speaker === "AI" ? "text-brand" : "text-white/70"
                  )}
                >
                  {entry.speaker}
                </span>
                <span className="text-[10px] text-white/30">{entry.timestamp}</span>
              </div>
              <p
                className={cn(
                  "text-xs leading-relaxed",
                  entry.speaker === "AI" ? "text-white/90" : "text-white/60"
                )}
              >
                {entry.text}
              </p>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

// ─── Round Transition Overlay ─────────────────────────────────────────────────

function RoundTransitionOverlay({
  completedRoundName,
  nextRoundName,
  countdown,
}: {
  completedRoundName: string;
  nextRoundName: string;
  countdown: number;
}) {
  return (
    <div className="fixed inset-0 z-50 bg-gray-950/95 flex items-center justify-center">
      <div className="text-center">
        <div className="flex justify-center mb-6">
          <div className="h-20 w-20 rounded-full bg-success-light flex items-center justify-center">
            <svg className="h-10 w-10 text-success" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
        </div>
        <h2 className="text-2xl font-bold text-white mb-1">
          Round Complete
        </h2>
        <p className="text-white/60 mb-8">{completedRoundName} round finished</p>

        {nextRoundName ? (
          <>
            <p className="text-white/80 text-lg">
              Starting Next Round: <span className="font-semibold text-brand">{nextRoundName}</span>
            </p>
            <div className="mt-6 h-14 w-14 rounded-full bg-brand/20 border-2 border-brand mx-auto flex items-center justify-center">
              <span className="text-2xl font-bold text-brand">{countdown}</span>
            </div>
          </>
        ) : (
          <p className="text-white/60">Finalizing your interview...</p>
        )}
      </div>
    </div>
  );
}

// ─── Main Interview Page ───────────────────────────────────────────────────────

export default function InterviewPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const [interview, setInterview] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState<any>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [isMicOn, setIsMicOn] = useState(true);
  const [isCameraOn, setIsCameraOn] = useState(true);
  const [timeRemaining, setTimeRemaining] = useState(45 * 60); // default to 45 min
  const [isEnding, setIsEnding] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);

  const [showTransition, setShowTransition] = useState(false);
  const [transitionCountdown, setTransitionCountdown] = useState(3);
  const [prevRoundLabel, setPrevRoundLabel] = useState("");
  const [nextRoundLabel, setNextRoundLabel] = useState("");

  const { phase, isRecording, isBotSpeaking, startGreeting, startRecording, stopRecording } = useSpeech({
    interviewId: interview?.id || "",
    onBotMessage: (text) => {
      setTranscript((prev) => [
        ...prev,
        {
          speaker: "AI",
          text,
          timestamp: now(),
        },
      ]);
    },
    onTranscript: (text) => {
      setTranscript((prev) => [
        ...prev,
        {
          speaker: "You",
          text,
          timestamp: now(),
        },
      ]);
    },
    onProgress: (prog) => {
      setProgress(prog);
    },
    onRoundChange: (newRound) => {
      const roundLabels: Record<string, string> = {
        intro: "Introduction",
        technical: "Technical",
        behavioral: "Behavioral",
        hr: "HR & Culture fit",
      };
      const prevRound = progress?.current_round || "intro";
      setPrevRoundLabel(roundLabels[prevRound] || prevRound);
      setNextRoundLabel(roundLabels[newRound] || newRound);
      setShowTransition(true);
      setTransitionCountdown(3);
    },
    onDone: () => {
      window.location.href = `/interview/${token}/done`;
    },
    onError: (err) => {
      setError(err);
    },
  });

  const videoRef = useFaceDetection({
    interviewId: interview?.id || "",
    enabled: isCameraOn && !!interview?.id,
  });

  // Load interview details on mount
  useEffect(() => {
    api.getInterviewByToken(token)
      .then(async (iv) => {
        setInterview(iv);
        if (iv.status === "scheduled") {
          await api.startInterview(iv.id);
        }
        if (iv.started_at) {
          const elapsed = Math.floor((Date.now() - new Date(iv.started_at).getTime()) / 1000);
          setTimeRemaining(Math.max(0, 45 * 60 - elapsed));
        }
      })
      .catch((err) => {
        console.error("Load interview error:", err);
        setError("Failed to load interview. Please make sure the link is correct.");
      })
      .finally(() => setLoading(false));
  }, [token]);

  // Start greeting when interview is loaded
  useEffect(() => {
    if (interview?.id && phase === "idle") {
      startGreeting();
    }
  }, [interview?.id, phase, startGreeting]);

  // Handle auto-recording when bot is done speaking
  useEffect(() => {
    if (phase === "listening" && !isRecording && isMicOn) {
      startRecording();
    }
  }, [phase, isRecording, isMicOn, startRecording]);

  // Stop recording when mic is muted
  useEffect(() => {
    if (!isMicOn && isRecording) {
      stopRecording();
    }
  }, [isMicOn, isRecording, stopRecording]);

  // Countdown timer
  useEffect(() => {
    const timer = setInterval(() => {
      setTimeRemaining((t) => Math.max(0, t - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Transition countdown timer
  useEffect(() => {
    if (!showTransition) return;
    const timer = setInterval(() => {
      setTransitionCountdown((c) => {
        if (c <= 1) {
          clearInterval(timer);
          setShowTransition(false);
          return 0;
        }
        return c - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [showTransition]);

  const currentRoundIndex = useMemo(() => {
    if (!progress) return 0;
    const order = ["intro", "technical", "behavioral", "hr"];
    const idx = order.indexOf(progress.current_round);
    return idx >= 0 ? idx : 0;
  }, [progress]);

  const currentQuestionText = useMemo(() => {
    const aiEntries = transcript.filter((t) => t.speaker === "AI");
    if (aiEntries.length === 0) return "Connecting with AI interviewer...";
    return aiEntries[aiEntries.length - 1].text;
  }, [transcript]);

  const handleEndInterview = useCallback(async () => {
    if (!interview?.id) return;
    setIsEnding(true);
    try {
      await api.completeInterview(interview.id);
    } catch (err) {
      console.error("Error completing interview:", err);
    }
    window.location.href = `/interview/${token}/done`;
  }, [interview?.id, token]);

  if (loading) {
    return (
      <div className="fixed inset-0 bg-gray-950 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-10 h-10 border-4 border-brand border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-white/60">Loading interview room...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-gray-950 flex items-center justify-center p-4">
        <div className="max-w-md w-full text-center space-y-6 bg-gray-900 border border-white/10 rounded-xl p-6">
          <div className="h-12 w-12 rounded-full bg-red-500/10 flex items-center justify-center mx-auto text-red-500">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div className="space-y-2">
            <h1 className="text-xl font-bold text-white">Interview Error</h1>
            <p className="text-sm text-white/60">{error}</p>
          </div>
          <Button asChild className="w-full">
            <Link href="/portal">Return to Portal</Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Round transition overlay */}
      {showTransition && (
        <RoundTransitionOverlay
          completedRoundName={prevRoundLabel}
          nextRoundName={nextRoundLabel}
          countdown={transitionCountdown}
        />
      )}

      {/* Full-screen dark layout */}
      <div className="fixed inset-0 bg-gray-950 flex flex-col overflow-hidden">
        {/* Top bar */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 shrink-0 z-10">
          <div className="flex items-center gap-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-brand">
              <svg className="h-4 w-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
                <path d="M3 18v-6a9 9 0 0 1 18 0v6" />
                <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z" />
              </svg>
            </div>
            <span className="text-sm font-semibold text-white hidden sm:inline">NexusAI Talent OS</span>
          </div>

          {/* Round + timer */}
          <div className="flex items-center gap-3">
            <span
              className={cn(
                "text-xs font-medium px-2.5 py-1 rounded-full",
                ROUND_COLORS[currentRoundIndex + 1] || "bg-brand-light text-brand"
              )}
            >
              {progress ? `Round ${currentRoundIndex + 1}: ${progress.round_label}` : "Initializing round..."}
            </span>
            <div className="flex items-center gap-1.5 text-white">
              <Clock className="h-4 w-4 text-white/50" />
              <span
                className={cn(
                  "text-sm font-mono font-semibold tabular-nums",
                  timeRemaining < 300 ? "text-error" : "text-white"
                )}
              >
                {formatSeconds(timeRemaining)}
              </span>
            </div>
            {/* Camera presence indicator */}
            <div className="flex items-center gap-1.5">
              <div
                className={cn(
                  "h-2 w-2 rounded-full",
                  isCameraOn ? "bg-success animate-pulse" : "bg-error"
                )}
              />
              <span className="text-[10px] text-white/40 hidden sm:inline">
                {isCameraOn ? "Camera active" : "Camera off"}
              </span>
            </div>
          </div>

          {/* Mobile transcript toggle */}
          <button
            className="flex lg:hidden items-center gap-1 text-xs text-white/60 hover:text-white/80 transition-colors"
            onClick={() => setShowTranscript((s) => !s)}
          >
            <MessageSquare className="h-4 w-4" />
          </button>
        </div>

        {/* Main content */}
        <div className="flex-1 flex min-h-0">
          {/* Left panel — video + question (70%) */}
          <div
            className={cn(
              "flex flex-col min-h-0",
              showTranscript ? "hidden" : "flex",
              "lg:flex lg:w-[70%]"
            )}
          >
            {/* Video area */}
            <div className="relative flex-1 bg-gray-900 min-h-0">
              {/* Main camera feed */}
              <div className="absolute inset-0 flex items-center justify-center">
                {isCameraOn ? (
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full bg-gray-950 flex flex-col items-center justify-center gap-3">
                    <CameraOff className="h-10 w-10 text-gray-700" />
                    <p className="text-sm text-gray-600">Camera is off</p>
                  </div>
                )}
              </div>

              {/* AI avatar pip */}
              <div className="absolute top-4 right-4 h-16 w-16 rounded-full border-2 border-white/10 overflow-hidden bg-gray-950">
                <AIAvatar isSpeaking={isBotSpeaking} />
              </div>

              {/* AI speaking indicator */}
              {isBotSpeaking && (
                <div className="absolute top-4 left-4 flex items-center gap-2 bg-black/60 backdrop-blur-sm rounded-full px-3 py-1.5">
                  <div className="flex gap-0.5 items-end h-3">
                    {[3, 5, 4, 6, 3].map((h, i) => (
                      <div
                        key={i}
                        className="w-0.5 bg-brand rounded-full animate-bounce"
                        style={{
                          height: `${h * 2}px`,
                          animationDelay: `${i * 0.1}s`,
                          animationDuration: "0.6s",
                        }}
                      />
                    ))}
                  </div>
                  <span className="text-xs text-white/80">AI Speaking</span>
                </div>
              )}

              {/* AI processing indicator */}
              {phase === "processing" && (
                <div className="absolute top-4 left-4 flex items-center gap-2 bg-black/60 backdrop-blur-sm rounded-full px-3 py-1.5">
                  <div className="w-3 h-3 border border-brand border-t-transparent rounded-full animate-spin" />
                  <span className="text-xs text-white/80">AI thinking...</span>
                </div>
              )}

              {/* User listening indicator */}
              {phase === "listening" && isRecording && (
                <div className="absolute top-4 left-4 flex items-center gap-2 bg-black/60 backdrop-blur-sm rounded-full px-3 py-1.5">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-brand"></span>
                  </span>
                  <span className="text-xs text-white/80">Listening... Speak now</span>
                </div>
              )}

              {/* Mic off indicator */}
              {!isMicOn && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 bg-error/90 rounded-full px-3 py-1.5">
                  <MicOff className="h-3.5 w-3.5 text-white" />
                  <span className="text-xs text-white font-medium">Mic is muted</span>
                </div>
              )}
            </div>

            {/* Question card */}
            <div className="shrink-0 p-4 border-t border-white/10 bg-gray-950">
              <div className="bg-gray-900 rounded-xl border border-white/10 p-4">
                {/* Question meta */}
                <div className="flex items-center justify-between gap-2 mb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-white/40 font-medium">
                      Question {progress ? progress.question_in_round : 1}
                    </span>
                    <div className="w-px h-3 bg-white/10" />
                    <span className="text-xs text-white/50 bg-white/5 px-2 py-0.5 rounded-full">
                      {progress ? progress.round_label : "Introduction"}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-warning-light text-warning">
                      Adaptive
                    </span>
                  </div>
                </div>

                {/* Question text */}
                <p className="text-white text-base leading-relaxed font-medium">
                  {currentQuestionText}
                </p>
              </div>

              {/* Controls */}
              <div className="flex items-center justify-between mt-4">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setIsMicOn((v) => !v)}
                    className={cn(
                      "h-10 w-10 rounded-full flex items-center justify-center transition-colors",
                      isMicOn
                        ? "bg-white/10 text-white hover:bg-white/20"
                        : "bg-error text-white hover:bg-red-700"
                    )}
                  >
                    {isMicOn ? <Mic className="h-4 w-4" /> : <MicOff className="h-4 w-4" />}
                  </button>
                  <button
                    onClick={() => setIsCameraOn((v) => !v)}
                    className={cn(
                      "h-10 w-10 rounded-full flex items-center justify-center transition-colors",
                      isCameraOn
                        ? "bg-white/10 text-white hover:bg-white/20"
                        : "bg-error text-white hover:bg-red-700"
                    )}
                  >
                    {isCameraOn ? <Camera className="h-4 w-4" /> : <CameraOff className="h-4 w-4" />}
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={stopRecording}
                    disabled={phase !== "listening" || !isRecording}
                    className="flex items-center gap-1.5 text-sm font-medium text-white bg-white/10 hover:bg-white/20 transition-colors px-4 py-2 rounded-full disabled:opacity-50"
                  >
                    <span>Submit Answer</span>
                    <ChevronRight className="h-4 w-4" />
                  </button>
                  <button
                    onClick={handleEndInterview}
                    disabled={isEnding}
                    className="flex items-center gap-1.5 text-sm font-medium text-white bg-error hover:bg-red-700 transition-colors px-4 py-2 rounded-full disabled:opacity-60"
                  >
                    <PhoneOff className="h-4 w-4" />
                    End
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Right panel — rounds + timer + transcript (30%) */}
          <div
            className={cn(
              "flex flex-col bg-gray-900 border-l border-white/10 min-h-0",
              showTranscript ? "flex w-full" : "hidden",
              "lg:flex lg:w-[30%]"
            )}
          >
            {/* Round progress */}
            <div className="p-4 border-b border-white/10 shrink-0">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold text-white/60 uppercase tracking-wider">
                  Progress
                </span>
                <span className="text-xs text-white/40">
                  Round {currentRoundIndex + 1}/{ROUNDS.length}
                </span>
              </div>
              <div className="space-y-2">
                {ROUNDS.map((round, i) => {
                  const done = i < currentRoundIndex;
                  const active = i === currentRoundIndex;
                  return (
                    <div key={round.id} className="flex items-center gap-2.5">
                      <div
                        className={cn(
                          "h-6 w-6 rounded-full flex items-center justify-center shrink-0 text-[10px] font-bold",
                          done && "bg-brand text-white",
                          active && "bg-brand text-white ring-2 ring-brand/30",
                          !done && !active && "bg-white/10 text-white/30"
                        )}
                      >
                        {done ? (
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        ) : (
                          round.id
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p
                          className={cn(
                            "text-xs font-medium truncate",
                            active ? "text-white" : done ? "text-white/50" : "text-white/30"
                          )}
                        >
                          {round.name}
                        </p>
                        {active && progress && (
                          <p className="text-[10px] text-white/40 mt-0.5">
                            Q{progress.question_in_round}/{progress.total_in_round}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Big timer */}
            <div className="px-4 py-3 border-b border-white/10 shrink-0">
              <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">
                Time Remaining
              </p>
              <div className="flex items-end gap-2">
                <span
                  className={cn(
                    "text-3xl font-mono font-bold tabular-nums",
                    timeRemaining < 300
                      ? "text-error"
                      : timeRemaining < 600
                      ? "text-warning"
                      : "text-white"
                  )}
                >
                  {formatSeconds(timeRemaining)}
                </span>
                <span className="text-xs text-white/30 mb-1">min</span>
              </div>
            </div>

            {/* Transcript */}
            <div className="flex-1 min-h-0 overflow-hidden">
              <TranscriptPanel entries={transcript} />
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

