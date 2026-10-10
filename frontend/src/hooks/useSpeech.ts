// src/hooks/useSpeech.ts
"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, playBase64Audio } from "@/lib/api";

const SILENCE_THRESHOLD = 0.012;
const SILENCE_DURATION  = 4000;
const MIN_BLOB_BYTES     = 300;

export type InterviewPhase =
  | "idle" | "greeting" | "listening" | "processing" | "bot-speaking" | "done";

interface RoundProgress {
  current_round: string;
  round_label: string;
  question_in_round: number;
  total_in_round: number;
  rounds_completed: number;
  total_rounds: number;
}

interface UseSpeechOptions {
  interviewId: string;
  onBotMessage?: (text: string, isFollowUp: boolean, followUpNum?: number) => void;
  onRoundChange?: (newRound: string) => void;
  onDone?: () => void;
  onError?: (msg: string) => void;
  onTranscript?: (text: string) => void;
  onProgress?: (progress: RoundProgress) => void;
}

export function useSpeech({
  interviewId, onBotMessage, onRoundChange, onDone, onError, onTranscript, onProgress,
}: UseSpeechOptions) {
  const [phase, setPhase] = useState<InterviewPhase>("idle");
  const [isRecording, setIsRecording] = useState(false);
  const [isBotSpeaking, setIsBotSpeaking] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef   = useRef<Blob[]>([]);
  const streamRef        = useRef<MediaStream | null>(null);
  const audioContextRef  = useRef<AudioContext | null>(null);
  const animFrameRef     = useRef<number | null>(null);
  const resultSentRef    = useRef(false);

  useEffect(() => () => {
    stopSilenceDetection();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    audioContextRef.current?.close().catch(() => {});
  }, []);

  function startSilenceDetection(stream: MediaStream, onSilence: () => void) {
    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      audioContextRef.current = ctx;

      const buf = new Float32Array(analyser.fftSize);
      let silenceStart: number | null = null;

      const check = () => {
        analyser.getFloatTimeDomainData(buf);
        const rms = Math.sqrt(buf.reduce((s, v) => s + v * v, 0) / buf.length);
        if (rms < SILENCE_THRESHOLD) {
          if (!silenceStart) silenceStart = Date.now();
          else if (Date.now() - silenceStart > SILENCE_DURATION) { onSilence(); return; }
        } else silenceStart = null;
        animFrameRef.current = requestAnimationFrame(check);
      };
      animFrameRef.current = requestAnimationFrame(check);
    } catch (e) {
      console.warn("Silence detection unavailable:", e);
    }
  }

  function stopSilenceDetection() {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
  }

  const callConversation = useCallback(async (transcript: string | null) => {
    setPhase("processing");
    try {
      const res = await api.conversationStep(interviewId, transcript);
      setPhase("bot-speaking");
      setIsBotSpeaking(true);

      onBotMessage?.(res.bot_text, res.is_follow_up, res.follow_up_number);
      onProgress?.(res.round_progress);
      if (res.round_changed && res.new_round) onRoundChange?.(res.new_round);

      await playBase64Audio(res.audio);
      setIsBotSpeaking(false);

      if (res.done) { setPhase("done"); onDone?.(); }
      else setPhase("listening");

      return res;
    } catch (err: any) {
      onError?.(err.message);
      setPhase("listening");
    }
  }, [interviewId, onBotMessage, onProgress, onRoundChange, onDone, onError]);

  const startGreeting = useCallback(async () => {
    setPhase("greeting");
    await callConversation(null);
  }, [callConversation]);

  const startRecording = useCallback(async () => {
    if (isRecording || isBotSpeaking) return;
    resultSentRef.current = false;
    audioChunksRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus" : "audio/webm",
      });
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };

      recorder.onstop = async () => {
        if (resultSentRef.current) return;
        resultSentRef.current = true;
        stopSilenceDetection();
        stream.getTracks().forEach((t) => t.stop());
        setIsRecording(false);

        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        if (blob.size < MIN_BLOB_BYTES) { setPhase("listening"); return; }

        try {
          const { transcript } = await api.transcribe(blob);
          if (transcript?.trim()) {
            onTranscript?.(transcript);
            await callConversation(transcript);
          } else setPhase("listening");
        } catch (err: any) {
          onError?.(err.message);
          setPhase("listening");
        }
      };

      recorder.start(250);
      setIsRecording(true);
      setPhase("listening");
      startSilenceDetection(stream, () => {
        if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
      });
    } catch (err: any) {
      onError?.(`Microphone error: ${err.message}`);
    }
  }, [isRecording, isBotSpeaking, callConversation, onTranscript, onError]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
  }, []);

  return { phase, isRecording, isBotSpeaking, startGreeting, startRecording, stopRecording };
}
