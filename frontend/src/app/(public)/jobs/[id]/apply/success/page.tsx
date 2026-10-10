import Link from "next/link";
import { CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const JOB_TITLES: Record<string, string> = {
  "1": "Senior Full-Stack Engineer",
  "2": "AI/ML Engineer",
  "3": "Product Designer",
  "4": "DevOps Engineer",
  "5": "Backend Engineer — Python",
  "6": "Growth Marketing Manager",
};

export default async function ApplicationSuccessPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const jobTitle = JOB_TITLES[id] ?? "this position";

  return (
    <div className="mx-auto max-w-lg px-4 sm:px-6 lg:px-8 py-20">
      <Card>
        <CardContent className="p-8 flex flex-col items-center text-center gap-6">
          {/* Animated checkmark */}
          <div className="animate-[fadeIn_0.4s_ease-out]">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-success-light">
              <CheckCircle2
                className="h-10 w-10 text-success"
                strokeWidth={1.5}
              />
            </div>
          </div>

          {/* Heading */}
          <div className="flex flex-col gap-2">
            <h1 className="text-2xl font-bold text-text-primary">
              Application Submitted!
            </h1>
            <p className="text-sm text-text-muted leading-relaxed">
              Thanks for applying for{" "}
              <span className="font-medium text-text-primary">{jobTitle}</span>.
              We&apos;ll review your application and get back to you within 24 hours.
            </p>
          </div>

          {/* Info box */}
          <div className="w-full rounded-lg border border-border bg-bg p-4 text-left">
            <p className="text-sm font-semibold text-text-primary mb-2">What happens next?</p>
            <ol className="flex flex-col gap-2">
              {[
                "Our AI reviews your resume against the job requirements",
                "If shortlisted, you'll receive an email with a link to schedule your interview",
                "Complete a 35–52 min AI-conducted interview at your chosen time",
                "Receive your assessment report within 24 hours of completing the interview",
              ].map((step, i) => (
                <li key={i} className="flex items-start gap-2.5 text-sm text-text-muted">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-light text-xs font-bold text-brand">
                    {i + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          </div>

          {/* CTAs */}
          <div className="flex w-full flex-col sm:flex-row gap-3">
            <Button asChild variant="secondary" size="lg" className="flex-1">
              <Link href={`/jobs/${id}`}>View Job Listing</Link>
            </Button>
            <Button asChild size="lg" className="flex-1">
              <Link href="/jobs">Browse More Jobs</Link>
            </Button>
          </div>

          {/* Reference note */}
          <p className="text-xs text-text-muted">
            A confirmation email has been sent to your inbox.
            Check your spam folder if you don&apos;t see it within a few minutes.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
