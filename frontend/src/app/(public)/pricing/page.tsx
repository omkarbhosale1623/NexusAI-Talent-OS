"use client";

import { useEffect, useState } from "react";
import { Check, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

type Plan = {
  plan: string;
  name: string;
  amount_cents: number;
  interval: string;
  features: string[];
};

const HIGHLIGHT = "pro"; // most-popular badge

function priceLabel(cents: number): string {
  return `$${(cents / 100).toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

export default function PricingPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [available, setAvailable] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getPlans()
      .then((r: any) => {
        setPlans(r.plans || []);
        setAvailable(Boolean(r.available));
      })
      .catch(() => setError("Could not load plans. Please try again later."))
      .finally(() => setLoading(false));
  }, []);

  async function subscribe(plan: string) {
    setBusy(plan);
    setError(null);
    try {
      // 401 → api client redirects to /login automatically.
      const r: any = await api.createCheckout(plan);
      if (r?.ok && r?.url) {
        window.location.href = r.url; // Stripe-hosted checkout
      } else {
        setError(
          r?.reason === "billing_not_configured"
            ? "Online payment is not configured yet — contact sales to activate this plan."
            : r?.reason || "Could not start checkout."
        );
      }
    } catch (e: any) {
      setError(e?.message || "Could not start checkout.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-14">
      <div className="mb-10 text-center">
        <h1 className="text-3xl font-bold text-text-primary">Plans &amp; Pricing</h1>
        <p className="mt-2 text-base text-text-muted">
          Start screening and interviewing with AI today. Upgrade any time.
        </p>
      </div>

      {error && (
        <p className="mb-6 text-center text-sm text-error">{error}</p>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {plans.map((p) => {
            const highlighted = p.plan === HIGHLIGHT;
            return (
              <Card
                key={p.plan}
                className={cn(
                  "flex flex-col",
                  highlighted && "border-brand shadow-md"
                )}
              >
                <CardContent className="flex flex-1 flex-col gap-5 p-6">
                  <div className="flex items-center justify-between">
                    <h2 className="text-lg font-semibold text-text-primary">{p.name}</h2>
                    {highlighted && (
                      <Badge className="gap-1">
                        <Sparkles className="h-3 w-3" />
                        Most popular
                      </Badge>
                    )}
                  </div>

                  <div>
                    <span className="text-4xl font-bold text-text-primary">
                      {priceLabel(p.amount_cents)}
                    </span>
                    <span className="text-sm text-text-muted">/{p.interval}</span>
                    {p.plan === "enterprise" && (
                      <p className="mt-1 text-xs text-text-muted">+ one-time setup, invoiced</p>
                    )}
                  </div>

                  <ul className="flex flex-col gap-2.5">
                    {p.features.map((f) => (
                      <li key={f} className="flex items-start gap-2 text-sm text-text-primary">
                        <Check className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                        {f}
                      </li>
                    ))}
                  </ul>

                  <div className="mt-auto pt-2">
                    <Button
                      className="w-full"
                      variant={highlighted ? "default" : "secondary"}
                      disabled={busy !== null}
                      onClick={() => subscribe(p.plan)}
                    >
                      {busy === p.plan ? "Redirecting…" : `Choose ${p.name}`}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <p className="mt-10 text-center text-xs text-text-muted">
        Payments are processed securely by Stripe. Subscriptions activate your
        organization&apos;s plan automatically after checkout
        {available ? "" : " (checkout is currently in setup mode)"}.
      </p>
    </div>
  );
}
