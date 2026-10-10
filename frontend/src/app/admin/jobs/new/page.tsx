"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, X, Plus, MapPin, Briefcase, DollarSign, Sparkles, Upload, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

const DEPARTMENTS = [
  "Engineering",
  "AI/ML",
  "Product",
  "Design",
  "Data",
  "Infrastructure",
  "Sales",
  "Marketing",
];

const EDUCATION_OPTIONS = [
  "Any",
  "High School",
  "Bachelor's Degree",
  "Master's Degree",
  "PhD",
];

const CURRENCIES = ["INR", "USD", "EUR", "GBP"];

type RoundKey = "introduction" | "technical" | "behavioral" | "hr";

const ROUNDS: { key: RoundKey; label: string; description: string }[] = [
  { key: "introduction", label: "Introduction", description: "Candidate introduction & background" },
  { key: "technical", label: "Technical", description: "Role-specific technical assessment" },
  { key: "behavioral", label: "Behavioral", description: "STAR-method behavioral questions" },
  { key: "hr", label: "HR & Culture", description: "Culture fit, salary, availability" },
];

const DURATION_OPTIONS = [5, 10, 15, 20, 25, 30];

interface RoundConfig {
  enabled: boolean;
  duration: number;
}

export default function NewJobPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [location, setLocation] = useState("");
  const [jobType, setJobType] = useState<"remote" | "hybrid" | "onsite">("remote");
  const [description, setDescription] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState("");
  const [expMin, setExpMin] = useState("2");
  const [expMax, setExpMax] = useState("5");
  const [education, setEducation] = useState("Bachelor's Degree");
  const [salaryMin, setSalaryMin] = useState("");
  const [salaryMax, setSalaryMax] = useState("");
  const [currency, setCurrency] = useState("INR");
  const [threshold, setThreshold] = useState(60);
  const [jdText, setJdText] = useState("");
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [parsing, setParsing] = useState(false);
  const [rounds, setRounds] = useState<Record<RoundKey, RoundConfig>>({
    introduction: { enabled: true, duration: 7 },
    technical: { enabled: true, duration: 20 },
    behavioral: { enabled: true, duration: 15 },
    hr: { enabled: true, duration: 10 },
  });

  function addSkill(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      const val = skillInput.trim();
      if (val && !skills.includes(val)) {
        setSkills((prev) => [...prev, val]);
      }
      setSkillInput("");
    }
  }

  function removeSkill(s: string) {
    setSkills((prev) => prev.filter((x) => x !== s));
  }

  function toggleRound(key: RoundKey) {
    setRounds((prev) => ({
      ...prev,
      [key]: { ...prev[key], enabled: !prev[key].enabled },
    }));
  }

  function setDuration(key: RoundKey, val: number) {
    setRounds((prev) => ({
      ...prev,
      [key]: { ...prev[key], duration: val },
    }));
  }

  async function handleJdParse() {
    if (!jdText && !jdFile) {
      setError("Please paste JD text or select a file to parse.");
      return;
    }
    setParsing(true);
    setError("");
    try {
      const parsed = await api.parseJd(jdText || undefined, jdFile || undefined);
      if (parsed.title) setTitle(parsed.title);
      if (parsed.required_skills && Array.isArray(parsed.required_skills)) {
        setSkills(parsed.required_skills);
      }
      if (parsed.years_experience_min !== undefined) {
        setExpMin(String(parsed.years_experience_min));
      }
      let desc = "";
      if (parsed.core_responsibilities && Array.isArray(parsed.core_responsibilities)) {
        desc += "Core Responsibilities:\n" + parsed.core_responsibilities.map((r: string) => `• ${r}`).join("\n") + "\n\n";
      }
      if (parsed.tech_stack && Array.isArray(parsed.tech_stack)) {
        desc += "Technology Stack:\n" + parsed.tech_stack.map((t: string) => `• ${t}`).join("\n");
      }
      if (desc) {
        setDescription(desc.trim());
      } else if (parsed.description) {
        setDescription(parsed.description);
      }
      setJdText("");
      setJdFile(null);
    } catch (err: any) {
      setError(err.message || "Failed to parse job description with AI.");
    } finally {
      setParsing(false);
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          href="/admin/jobs"
          className="flex h-8 w-8 items-center justify-center rounded-md text-text-muted hover:bg-border hover:text-text-primary transition-colors duration-100"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-text-primary">
            Create Job Posting
          </h1>
          <p className="text-sm text-text-muted mt-0.5">
            Fill in the details to publish a new job opening.
          </p>
        </div>
      </div>

      {/* AI JD Auto-Fill Section */}
      <Card className="border border-brand/20 bg-brand-light/10 shadow-sm relative overflow-hidden">
        <div className="absolute right-0 top-0 translate-x-1/4 -translate-y-1/4 w-32 h-32 bg-brand/5 rounded-full blur-2xl pointer-events-none" />
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold flex items-center gap-2 text-brand">
            <Sparkles className="h-4.5 w-4.5 text-brand animate-pulse" />
            AI Job Description Import
          </CardTitle>
          <p className="text-xs text-text-muted mt-0.5">
            Paste job text or upload a JD document. Our AI will parse the details and auto-fill the forms below!
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-text-primary">
                Paste JD Text
              </label>
              <Textarea
                placeholder="Paste the job description content here..."
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                rows={3}
                className="text-xs resize-none"
                disabled={parsing}
              />
            </div>
            <div className="space-y-1.5 flex flex-col justify-between">
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-text-primary">
                  Or Upload JD File (PDF, DOCX, TXT)
                </label>
                <div className="relative border border-dashed border-border rounded-lg p-4 flex flex-col items-center justify-center bg-bg/50 hover:bg-bg/80 transition-colors cursor-pointer">
                  <input
                    type="file"
                    accept=".pdf,.docx,.doc,.txt"
                    onChange={(e) => setJdFile(e.target.files?.[0] || null)}
                    className="absolute inset-0 opacity-0 cursor-pointer"
                    disabled={parsing}
                  />
                  {jdFile ? (
                    <div className="flex items-center gap-2 text-brand">
                      <FileText className="h-5 w-5 text-brand" />
                      <span className="text-xs font-semibold truncate max-w-[200px]">
                        {jdFile.name}
                      </span>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          setJdFile(null);
                        }}
                        className="text-text-muted hover:text-error transition-colors"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ) : (
                    <>
                      <Upload className="h-5 w-5 text-text-muted mb-1" />
                      <span className="text-xs text-text-muted">
                        Click or drag file here
                      </span>
                    </>
                  )}
                </div>
              </div>
              <Button
                type="button"
                onClick={handleJdParse}
                loading={parsing}
                className="w-full text-xs h-9 bg-brand hover:bg-brand-hover text-white flex items-center justify-center gap-1.5 self-end"
                disabled={!jdText && !jdFile}
              >
                <Sparkles className="h-3.5 w-3.5" />
                AI Parse & Auto-fill
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Basic Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Briefcase className="h-4 w-4 text-text-muted" />
            Basic Information
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1.5">
              Job Title <span className="text-error">*</span>
            </label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Senior Frontend Engineer"
            />
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1.5">
                Department
              </label>
              <select
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="flex h-10 w-full rounded-lg border border-input-border bg-surface px-3 py-2 text-sm text-text-primary focus:border-brand focus:ring-1 focus:ring-brand/20 transition-all duration-100"
              >
                <option value="">Select department</option>
                {DEPARTMENTS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1.5">
                Location
              </label>
              <div className="relative">
                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
                <Input
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="e.g. Bangalore, India"
                  className="pl-9"
                />
              </div>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              Job Type
            </label>
            <div className="flex gap-3">
              {(["remote", "hybrid", "onsite"] as const).map((type) => (
                <label
                  key={type}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2.5 rounded-lg border cursor-pointer text-sm font-medium transition-all duration-100 capitalize",
                    jobType === type
                      ? "border-brand bg-brand-light text-brand"
                      : "border-border text-text-muted hover:border-brand/40"
                  )}
                >
                  <input
                    type="radio"
                    name="jobType"
                    value={type}
                    checked={jobType === type}
                    onChange={() => setJobType(type)}
                    className="sr-only"
                  />
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </label>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Description */}
      <Card>
        <CardHeader>
          <CardTitle>Description</CardTitle>
        </CardHeader>
        <CardContent>
          <label className="block text-sm font-medium text-text-primary mb-1.5">
            Job Description <span className="text-error">*</span>
          </label>
          <Textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the role, responsibilities, and what the team does..."
            rows={6}
          />
          <p className="text-xs text-text-muted mt-1.5">
            {description.length} characters
          </p>
        </CardContent>
      </Card>

      {/* Requirements */}
      <Card>
        <CardHeader>
          <CardTitle>Requirements</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1.5">
              Required Skills
            </label>
            <div
              className={cn(
                "flex flex-wrap gap-2 min-h-[44px] rounded-lg border border-input-border bg-surface px-3 py-2 focus-within:border-brand focus-within:ring-1 focus-within:ring-brand/20 transition-all duration-100"
              )}
            >
              {skills.map((s) => (
                <span
                  key={s}
                  className="inline-flex items-center gap-1 rounded-full bg-brand-light text-brand px-2.5 py-0.5 text-xs font-medium"
                >
                  {s}
                  <button
                    onClick={() => removeSkill(s)}
                    className="hover:text-brand-hover"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
              <input
                value={skillInput}
                onChange={(e) => setSkillInput(e.target.value)}
                onKeyDown={addSkill}
                placeholder={
                  skills.length === 0
                    ? "Type a skill and press Enter..."
                    : "Add more..."
                }
                className="flex-1 min-w-[120px] bg-transparent text-sm text-text-primary placeholder:text-text-muted focus:outline-none"
              />
            </div>
            <p className="text-xs text-text-muted mt-1">
              Press Enter or comma to add a skill
            </p>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1.5">
                Experience Range (years)
              </label>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  value={expMin}
                  onChange={(e) => setExpMin(e.target.value)}
                  min={0}
                  className="w-24"
                />
                <span className="text-sm text-text-muted">to</span>
                <Input
                  type="number"
                  value={expMax}
                  onChange={(e) => setExpMax(e.target.value)}
                  min={0}
                  className="w-24"
                />
                <span className="text-sm text-text-muted">years</span>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1.5">
                Education Requirement
              </label>
              <select
                value={education}
                onChange={(e) => setEducation(e.target.value)}
                className="flex h-10 w-full rounded-lg border border-input-border bg-surface px-3 text-sm text-text-primary focus:border-brand focus:ring-1 focus:ring-brand/20 transition-all duration-100"
              >
                {EDUCATION_OPTIONS.map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Compensation */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-text-muted" />
            Compensation
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="h-10 rounded-lg border border-input-border bg-surface px-3 text-sm text-text-primary focus:border-brand focus:ring-1 focus:ring-brand/20 transition-all duration-100"
            >
              {CURRENCIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <Input
              type="number"
              value={salaryMin}
              onChange={(e) => setSalaryMin(e.target.value)}
              placeholder="Min salary"
              className="w-36"
            />
            <span className="text-sm text-text-muted">to</span>
            <Input
              type="number"
              value={salaryMax}
              onChange={(e) => setSalaryMax(e.target.value)}
              placeholder="Max salary"
              className="w-36"
            />
            <span className="text-sm text-text-muted">per year</span>
          </div>
        </CardContent>
      </Card>

      {/* Interview Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Interview Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Rounds */}
          <div className="space-y-3">
            {ROUNDS.map((round) => {
              const cfg = rounds[round.key];
              return (
                <div
                  key={round.key}
                  className={cn(
                    "rounded-lg border p-4 transition-all duration-100",
                    cfg.enabled ? "border-brand bg-brand-light/30" : "border-border"
                  )}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <button
                        onClick={() => toggleRound(round.key)}
                        className={cn(
                          "mt-0.5 flex h-5 w-9 shrink-0 items-center rounded-full border-2 p-0.5 transition-all duration-200",
                          cfg.enabled
                            ? "border-brand bg-brand"
                            : "border-border bg-border"
                        )}
                      >
                        <span
                          className={cn(
                            "h-3.5 w-3.5 rounded-full bg-white shadow transition-transform duration-200",
                            cfg.enabled ? "translate-x-4" : "translate-x-0"
                          )}
                        />
                      </button>
                      <div>
                        <p className="text-sm font-semibold text-text-primary">
                          {round.label}
                        </p>
                        <p className="text-xs text-text-muted mt-0.5">
                          {round.description}
                        </p>
                      </div>
                    </div>
                    {cfg.enabled && (
                      <div className="flex items-center gap-2 shrink-0">
                        <label className="text-xs text-text-muted">Duration:</label>
                        <select
                          value={cfg.duration}
                          onChange={(e) =>
                            setDuration(round.key, Number(e.target.value))
                          }
                          className="h-8 rounded-md border border-input-border bg-surface px-2 text-sm text-text-primary focus:border-brand focus:outline-none"
                        >
                          {DURATION_OPTIONS.map((d) => (
                            <option key={d} value={d}>
                              {d} min
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Threshold */}
          <div className="pt-2">
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-text-primary">
                Eligibility Threshold
              </label>
              <span className="text-sm font-bold text-brand tabular-nums">
                {threshold}%
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="w-full h-2 rounded-full bg-border appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-brand [&::-webkit-slider-thumb]:shadow"
            />
            <p className="text-xs text-text-muted mt-1.5">
              Candidates below this eligibility score will be automatically rejected.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Preview */}
      {title && (
        <Card>
          <CardHeader>
            <CardTitle>Preview</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border border-border bg-bg p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-base font-bold text-text-primary">
                    {title || "Job Title"}
                  </h2>
                  <div className="flex flex-wrap gap-3 mt-1.5">
                    {department && (
                      <span className="text-sm text-text-muted">{department}</span>
                    )}
                    {location && (
                      <span className="flex items-center gap-1 text-sm text-text-muted">
                        <MapPin className="h-3.5 w-3.5" />
                        {location}
                      </span>
                    )}
                    {jobType && (
                      <span className="capitalize text-sm text-text-muted">
                        {jobType}
                      </span>
                    )}
                  </div>
                  {skills.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {skills.slice(0, 5).map((s) => (
                        <span
                          key={s}
                          className="text-xs bg-border text-text-muted px-2 py-0.5 rounded-full"
                        >
                          {s}
                        </span>
                      ))}
                      {skills.length > 5 && (
                        <span className="text-xs text-text-muted">
                          +{skills.length - 5} more
                        </span>
                      )}
                    </div>
                  )}
                </div>
                {salaryMin && salaryMax && (
                  <div className="text-right">
                    <p className="text-sm font-semibold text-text-primary">
                      {currency} {Number(salaryMin).toLocaleString()} –{" "}
                      {Number(salaryMax).toLocaleString()}
                    </p>
                    <p className="text-xs text-text-muted">per year</p>
                  </div>
                )}
              </div>
              {description && (
                <p className="text-sm text-text-muted mt-3 line-clamp-3">
                  {description}
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      {error && (
        <div className="rounded-lg bg-error-light border border-error/20 px-4 py-3">
          <p className="text-sm text-error font-medium">{error}</p>
        </div>
      )}
      <div className="flex items-center justify-end gap-3 pb-8">
        <Button
          variant="secondary"
          loading={submitting}
          onClick={async () => {
            setSubmitting(true);
            setError("");
            try {
              await api.createJob({
                title,
                department,
                location,
                employment_type: jobType,
                description,
                required_skills: skills,
                experience_min: Number(expMin),
                experience_max: Number(expMax),
                salary_min: Number(salaryMin) || 0,
                salary_max: Number(salaryMax) || 0,
                status: "draft",
                rounds_config: Object.fromEntries(
                  Object.entries(rounds)
                    .filter(([, v]) => v.enabled)
                    .map(([k, v]) => [k, { duration_minutes: v.duration, enabled: true }])
                ),
              });
              router.push("/admin/jobs");
            } catch (err: any) {
              setError(err.message);
            } finally {
              setSubmitting(false);
            }
          }}
        >
          Save as Draft
        </Button>
        <Button
          loading={submitting}
          onClick={async () => {
            setSubmitting(true);
            setError("");
            try {
              await api.createJob({
                title,
                department,
                location,
                employment_type: jobType,
                description,
                required_skills: skills,
                experience_min: Number(expMin),
                experience_max: Number(expMax),
                salary_min: Number(salaryMin) || 0,
                salary_max: Number(salaryMax) || 0,
                status: "published",
                rounds_config: Object.fromEntries(
                  Object.entries(rounds)
                    .filter(([, v]) => v.enabled)
                    .map(([k, v]) => [k, { duration_minutes: v.duration, enabled: true }])
                ),
              });
              router.push("/admin/jobs");
            } catch (err: any) {
              setError(err.message);
            } finally {
              setSubmitting(false);
            }
          }}
        >
          <Plus className="h-4 w-4" />
          Publish Job
        </Button>
      </div>
    </div>
  );
}
