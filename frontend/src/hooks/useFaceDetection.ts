// src/hooks/useFaceDetection.ts
// Client-side proctoring: face detection + browser event tracking.
// Sends violations to backend webhook. No ML model training required —
// uses MediaPipe's pre-trained face detector loaded from CDN.
"use client";
import { useEffect, useRef } from "react";

const NEXUSAI_API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface UseFaceDetectionOptions {
  interviewId: string;
  enabled: boolean;
  fps?: number;
}

async function sendProctoringEvent(interviewId: string, body: any) {
  try {
    await fetch(`${NEXUSAI_API}/webhooks/proctoring/${interviewId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    /* silent fail — never block the interview */
  }
}

export function useFaceDetection({ interviewId, enabled, fps = 1 }: UseFaceDetectionOptions) {
  const videoRef    = useRef<HTMLVideoElement>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const canvasRef   = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (!enabled || !interviewId) return;
    if (!canvasRef.current) canvasRef.current = document.createElement("canvas");

    let stream: MediaStream;
    navigator.mediaDevices.getUserMedia({ video: true }).then((s) => {
      stream = s;
      if (videoRef.current) videoRef.current.srcObject = s;

      intervalRef.current = setInterval(async () => {
        const video = videoRef.current;
        if (!video || video.readyState < 2) return;
        const canvas = canvasRef.current!;
        canvas.width = 320; canvas.height = 240;
        canvas.getContext("2d")?.drawImage(video, 0, 0, 320, 240);
        const frame = canvas.toDataURL("image/jpeg", 0.7).replace("data:image/jpeg;base64,", "");

        // Send to backend frame-analysis webhook (MediaPipe/YOLO run server-side)
        try {
          await fetch(`${NEXUSAI_API}/webhooks/proctoring/${interviewId}/frame`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ frame, timestamp: Date.now() / 1000 }),
          });
        } catch { /* silent */ }
      }, 1000 / fps);
    }).catch((err) => console.warn("Camera access denied:", err));

    const onVisibility = () => {
      if (document.hidden) {
        sendProctoringEvent(interviewId, {
          event_type: "TAB_SWITCH", confidence: 1.0,
          metadata: { action: "hidden" }, timestamp: new Date().toISOString(),
        });
      }
    };
    const onCopy = () => sendProctoringEvent(interviewId, {
      event_type: "COPY_PASTE", confidence: 1.0,
      metadata: { action: "copy" }, timestamp: new Date().toISOString(),
    });

    document.addEventListener("visibilitychange", onVisibility);
    document.addEventListener("copy", onCopy);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      document.removeEventListener("visibilitychange", onVisibility);
      document.removeEventListener("copy", onCopy);
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, [enabled, interviewId, fps]);

  return videoRef;
}
