"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import { ArrowLeft, Mail, Phone, Download, ExternalLink, Briefcase, GraduationCap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { ScoreBadge } from "@/components/ui/score-badge";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";
import { api } from "@/lib/api";
import { adaptApplication, adaptCandidate } from "@/lib/adapters";

const REC_LABELS: Record<string, string> = {
  strong_hire: "Strong Hire",
  hire: "Hire",
  maybe: "Maybe",
  no_hire: "No Hire",
};

export default function CandidateDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [candidate, setCandidate] = useState<any>(null);
  const [applications, setApplications] = useState<any[]>([]);
  const [interviews, setInterviews] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load application details
    api.getApplication(id)
      .then(async (app) => {
        // Retrieve candidate details
        const cand = app.candidate || await api.getCandidate(app.candidate_id);
        const parsed = app.parsed_resume || {};

        // Setup candidate profile info
        setCandidate({
          id: cand.id,
          name: cand.full_name || cand.name,
          email: cand.email,
          phone: cand.phone,
          currentRole: parsed.current_title || "Candidate",
          skills: [
            ...(parsed.skills || []),
            ...(parsed.programming_languages || []),
            ...(parsed.frameworks || [])
          ],
          experience: (parsed.companies || []).map((c: any) => ({
            company: c.name,
            role: c.title,
            start: `${c.duration_months || 0} months`,
            end: "",
            description: ""
          })),
          education: (parsed.education || []).map((e: any) => ({
            institution: e.institution,
            degree: e.degree,
            year: e.year
          })),
          projects: []
        });

        // Set applications list
        const appsList = await api.listApplications({ candidate_id: cand.id });
        setApplications((appsList.items || []).map((raw: any) => {
          const adapted = adaptApplication(raw);
          return {
            ...adapted,
            job_title: raw.job?.title || "—",
            company_name: raw.job?.org_name || "NexusAI"
          };
        }));

        // Fetch interviews for this candidate
        const ivsList = await api.listInterviews({ candidate_id: cand.id });
        setInterviews((ivsList.items || []).map((raw: any) => ({
          id: raw.id,
          job_title: raw.job?.title || "—",
          date: raw.scheduled_at || raw.created_at,
          duration: raw.duration_minutes || 60,
          score: raw.overall_score || 0,
          recommendation: raw.recommendation || "maybe",
          report_id: raw.id
        })));
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!candidate) {
    return (
      <div className="text-center py-16">
        <p className="text-text-muted font-medium">Candidate not found</p>
        <Link href="/admin/candidates" className="mt-4 text-brand underline inline-block">
          Back to Candidates
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <Link
          href="/admin/candidates"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-text-muted hover:bg-border hover:text-text-primary transition-colors duration-100 mt-1"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <Card className="flex-1 p-4">
          <div className="flex flex-wrap items-start gap-4">
            <Avatar size="lg" name={candidate.name} />
            <div className="flex-1 min-w-0">
              <h1 className="text-xl font-bold text-text-primary">
                {candidate.name}
              </h1>
              <p className="text-sm text-text-muted mt-0.5">
                {candidate.currentRole}
              </p>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2">
                <a
                  href={`mailto:${candidate.email}`}
                  className="flex items-center gap-1.5 text-sm text-text-muted hover:text-brand transition-colors duration-100"
                >
                  <Mail className="h-3.5 w-3.5" />
                  {candidate.email}
                </a>
                {candidate.phone && (
                  <span className="flex items-center gap-1.5 text-sm text-text-muted">
                    <Phone className="h-3.5 w-3.5" />
                    {candidate.phone}
                  </span>
                )}
              </div>
            </div>
            <Button variant="secondary" size="sm">
              <Download className="h-4 w-4" />
              Download Resume
            </Button>
          </div>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="profile">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="applications">
            Applications ({applications.length})
          </TabsTrigger>
          <TabsTrigger value="interviews">Interview History</TabsTrigger>
        </TabsList>

        {/* Profile */}
        <TabsContent value="profile">
          <div className="grid gap-5 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-5">
              {/* Experience */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Briefcase className="h-4 w-4 text-text-muted" />
                    Work Experience
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-5">
                  {candidate.experience.length === 0 ? (
                    <p className="text-sm text-text-muted">No experience details parsed.</p>
                  ) : (
                    candidate.experience.map((exp: any, i: number) => (
                      <div key={i} className="relative pl-4">
                        <div className="absolute left-0 top-1.5 h-2 w-2 rounded-full bg-brand" />
                        {i < candidate.experience.length - 1 && (
                          <div className="absolute left-[3px] top-4 bottom-[-16px] w-px bg-border" />
                        )}
                        <div>
                          <p className="text-sm font-semibold text-text-primary">
                            {exp.role}
                          </p>
                          <p className="text-sm text-brand">{exp.company}</p>
                          <p className="text-xs text-text-muted mt-0.5">
                            {exp.start} {exp.end ? `– ${exp.end}` : ""}
                          </p>
                          {exp.description && (
                            <p className="text-sm text-text-muted mt-1.5 leading-relaxed">
                              {exp.description}
                            </p>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>

              {/* Projects */}
              {candidate.projects.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Projects</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {candidate.projects.map((p: any, i: number) => (
                      <div key={i}>
                        <p className="text-sm font-semibold text-text-primary">
                          {p.name}
                        </p>
                        <p className="text-sm text-text-muted mt-0.5 leading-relaxed">
                          {p.desc}
                        </p>
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {p.techs.map((t: string) => (
                            <Badge key={t} variant="outline">
                              {t}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </div>

            <div className="space-y-5">
              {/* Skills */}
              <Card>
                <CardHeader>
                  <CardTitle>Skills</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-1.5">
                    {candidate.skills.length === 0 ? (
                      <p className="text-sm text-text-muted">No skills parsed.</p>
                    ) : (
                      candidate.skills.map((s: string) => (
                        <Badge key={s} variant="default">
                          {s}
                        </Badge>
                      ))
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Education */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <GraduationCap className="h-4 w-4 text-text-muted" />
                    Education
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {candidate.education.length === 0 ? (
                    <p className="text-sm text-text-muted">No education details parsed.</p>
                  ) : (
                    candidate.education.map((e: any, i: number) => (
                      <div key={i}>
                        <p className="text-sm font-semibold text-text-primary">
                          {e.degree}
                        </p>
                        <p className="text-sm text-text-muted">{e.institution}</p>
                        {e.year && (
                          <p className="text-xs text-text-muted mt-0.5">
                            Class of {e.year}
                          </p>
                        )}
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Applications */}
        <TabsContent value="applications">
          <Card className="overflow-hidden">
            <table className="w-full">
              <thead className="border-b border-border">
                <tr>
                  {["Job Title", "Score", "Status", "Applied"].map((h) => (
                    <th key={h} className="text-left px-5 py-3 text-xs font-medium text-text-muted uppercase tracking-wide">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {applications.map((a) => (
                  <tr key={a.id} className="hover:bg-bg transition-colors duration-100">
                    <td className="px-5 py-4">
                      <p className="text-sm font-medium text-text-primary">{a.job_title}</p>
                      <p className="text-xs text-text-muted">{a.company_name}</p>
                    </td>
                    <td className="px-5 py-4">
                      {a.eligibility_score != null && a.eligibility_score > 0 ? (
                        <ScoreBadge score={a.eligibility_score} size="sm" />
                      ) : (
                        <span className="text-xs text-text-muted">—</span>
                      )}
                    </td>
                    <td className="px-5 py-4">
                      <StatusBadge status={a.status} />
                    </td>
                    <td className="px-5 py-4 text-sm text-text-muted">
                      {formatDate(a.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </TabsContent>

        {/* Interview History */}
        <TabsContent value="interviews">
          <div className="space-y-3">
            {interviews.length === 0 ? (
              <Card className="p-5 text-center text-sm text-text-muted">
                No interviews recorded for this candidate.
              </Card>
            ) : (
              interviews.map((iv) => (
                <Card key={iv.id} className="p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-text-primary">
                        {iv.job_title}
                      </p>
                      <p className="text-xs text-text-muted mt-0.5">
                        {formatDate(iv.date)} · {iv.duration} min
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      {iv.score > 0 ? (
                        <ScoreBadge score={iv.score} size="sm" />
                      ) : (
                        <span className="text-xs text-text-muted">—</span>
                      )}
                      <span className="text-xs font-medium text-text-muted">
                        {REC_LABELS[iv.recommendation] || iv.recommendation}
                      </span>
                      <Link
                        href={`/admin/reports/${iv.report_id}`}
                        className="flex items-center gap-1 text-xs text-brand hover:text-brand-hover font-medium"
                      >
                        Report
                        <ExternalLink className="h-3 w-3" />
                      </Link>
                    </div>
                  </div>
                </Card>
              ))
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
