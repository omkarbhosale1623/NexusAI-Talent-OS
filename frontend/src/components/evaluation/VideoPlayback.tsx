"use client";

import { useEffect, useState } from "react";
import { Video } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/loading";

interface Props {
  interviewId: string;
}

export default function VideoPlayback({ interviewId }: Props) {
  const [loading, setLoading] = useState(true);
  const [url, setUrl] = useState<string | null>(null);
  const [reason, setReason] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setUrl(null);
    setReason(null);
    api
      .getRecordingPlayback(interviewId)
      .then((res: any) => {
        if (!active) return;
        if (res?.url) {
          setUrl(res.url);
        } else {
          setReason(res?.reason ?? "No recording available for this interview.");
        }
      })
      .catch((e: any) => {
        if (!active) return;
        setReason(e?.message ?? "Failed to load recording.");
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [interviewId]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Interview Recording</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Spinner className="py-10" />
        ) : url ? (
          <video
            controls
            src={url}
            className="w-full rounded-lg border border-border"
          />
        ) : (
          <EmptyState
            icon={Video}
            title="No recording available"
            description={reason ?? undefined}
          />
        )}
      </CardContent>
    </Card>
  );
}
