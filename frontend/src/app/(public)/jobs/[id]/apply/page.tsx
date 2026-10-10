"use client";

import { useState, useRef, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Upload, X, FileText, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface FormState {
  fullName: string;
  email: string;
  phone: string;
  currentRole: string;
  currentCompany: string;
  yearsOfExperience: string;
  expectedSalary: string;
  linkedinUrl: string;
}

interface FormErrors {
  fullName?: string;
  email?: string;
  phone?: string;
  yearsOfExperience?: string;
  expectedSalary?: string;
  resume?: string;
}

type Step = 1 | 2 | 3;

const JOB_TITLES: Record<string, string> = {
  "1": "Senior Full-Stack Engineer",
  "2": "AI/ML Engineer",
  "3": "Product Designer",
  "4": "DevOps Engineer",
  "5": "Backend Engineer — Python",
  "6": "Growth Marketing Manager",
};

const STEPS: { label: string; step: Step }[] = [
  { label: "Your Info", step: 1 },
  { label: "Resume", step: 2 },
  { label: "Submit", step: 3 },
];

// ─── Component ────────────────────────────────────────────────────────────────

export default function ApplyPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const jobTitle = JOB_TITLES[id] ?? "Open Position";

  const [currentStep, setCurrentStep] = useState<Step>(1);
  const [form, setForm] = useState<FormState>({
    fullName: "",
    email: "",
    phone: "",
    currentRole: "",
    currentCompany: "",
    yearsOfExperience: "",
    expectedSalary: "",
    linkedinUrl: "",
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [error, setError] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const update = (field: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  // ─── Validation ─────────────────────────────────────────────────────────────

  const validateStep1 = (): boolean => {
    const next: FormErrors = {};
    if (!form.fullName.trim()) next.fullName = "Full name is required";
    if (!form.email) next.email = "Email is required";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) next.email = "Enter a valid email";
    if (!form.phone.trim()) next.phone = "Phone number is required";
    if (!form.yearsOfExperience) next.yearsOfExperience = "Years of experience is required";
    if (!form.expectedSalary) next.expectedSalary = "Expected salary is required";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const validateStep2 = (): boolean => {
    if (!resumeFile) {
      setErrors({ resume: "Please upload your resume" });
      return false;
    }
    setErrors({});
    return true;
  };

  // ─── File handling ───────────────────────────────────────────────────────────

  const handleFile = (file: File) => {
    const allowed = ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"];
    if (!allowed.includes(file.type)) {
      setErrors({ resume: "Only PDF or DOCX files are accepted" });
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setErrors({ resume: "File size must be under 10 MB" });
      return;
    }
    setResumeFile(file);
    setErrors({});
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  // ─── Navigation ──────────────────────────────────────────────────────────────

  const goNext = () => {
    if (currentStep === 1 && validateStep1()) setCurrentStep(2);
    else if (currentStep === 2 && validateStep2()) setCurrentStep(3);
  };

  const handleSubmit = async () => {
    if (!resumeFile) return;
    setSubmitting(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("full_name", form.fullName);
      formData.append("email", form.email);
      formData.append("phone", form.phone);
      formData.append("years_experience", form.yearsOfExperience);
      formData.append("expected_salary", form.expectedSalary);
      if (form.linkedinUrl) {
        formData.append("linkedin_url", form.linkedinUrl);
      }
      formData.append("resume", resumeFile);

      await api.applyToJob(id, formData);
      router.push(`/jobs/${id}/apply/success`);
    } catch (err: any) {
      setError(err.message || "Failed to submit application.");
      setCurrentStep(1); // Go back to first step to fix errors
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-4 sm:px-6 lg:px-8 py-10">
      {/* Back */}
      <Link
        href={`/jobs/${id}`}
        className="inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-text-primary transition-colors mb-6"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to job listing
      </Link>

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary">
          Apply for{" "}
          <span className="text-brand">{jobTitle}</span>
        </h1>
        <p className="mt-1 text-sm text-text-muted">
          Fill in your details — our AI will review your application within 24 hours.
        </p>
      </div>

      {/* Progress indicator */}
      <div className="mb-8">
        <div className="flex items-center gap-0">
          {STEPS.map((s, i) => (
            <div key={s.step} className="flex items-center flex-1 last:flex-none">
              {/* Step circle */}
              <div className="flex flex-col items-center gap-1">
                <div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-colors duration-200",
                    currentStep > s.step
                      ? "bg-brand text-white"
                      : currentStep === s.step
                      ? "bg-brand text-white ring-4 ring-brand/20"
                      : "bg-border text-text-muted"
                  )}
                >
                  {currentStep > s.step ? <Check className="h-4 w-4" /> : s.step}
                </div>
                <span
                  className={cn(
                    "text-xs font-medium whitespace-nowrap",
                    currentStep === s.step ? "text-brand" : "text-text-muted"
                  )}
                >
                  {s.label}
                </span>
              </div>
              {/* Connector */}
              {i < STEPS.length - 1 && (
                <div
                  className={cn(
                    "flex-1 h-px mx-2 mb-5 transition-colors duration-200",
                    currentStep > s.step ? "bg-brand" : "bg-border"
                  )}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-error-light border border-error/20 px-4 py-3">
          <p className="text-sm text-error font-medium">{error}</p>
        </div>
      )}

      {/* Step 1 — Personal & Professional Info */}
      {currentStep === 1 && (
        <Card>
          <CardContent className="p-6 flex flex-col gap-5">
            <div>
              <h2 className="text-base font-semibold text-text-primary">Personal Information</h2>
              <p className="text-xs text-text-muted mt-0.5">Your contact details</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <label className="mb-1.5 block text-sm font-medium text-text-primary">
                  Full Name <span className="text-error">*</span>
                </label>
                <Input
                  placeholder="Omkar Bhosale"
                  value={form.fullName}
                  onChange={update("fullName")}
                  error={errors.fullName}
                />
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-text-primary">
                  Email Address <span className="text-error">*</span>
                </label>
                <Input
                  type="email"
                  placeholder="you@example.com"
                  value={form.email}
                  onChange={update("email")}
                  error={errors.email}
                />
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-text-primary">
                  Phone Number <span className="text-error">*</span>
                </label>
                <Input
                  type="tel"
                  placeholder="+91 9876543210"
                  value={form.phone}
                  onChange={update("phone")}
                  error={errors.phone}
                />
              </div>
            </div>

            <div className="h-px bg-border" />

            <div>
              <h2 className="text-base font-semibold text-text-primary">Professional Background</h2>
              <p className="text-xs text-text-muted mt-0.5">Your current role and expectations</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-text-primary">
                  Current Role
                </label>
                <Input
                  placeholder="Senior Engineer"
                  value={form.currentRole}
                  onChange={update("currentRole")}
                />
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-text-primary">
                  Current Company
                </label>
                <Input
                  placeholder="Acme Corp"
                  value={form.currentCompany}
                  onChange={update("currentCompany")}
                />
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-text-primary">
                  Years of Experience <span className="text-error">*</span>
                </label>
                <Input
                  type="number"
                  min="0"
                  max="40"
                  placeholder="4"
                  value={form.yearsOfExperience}
                  onChange={update("yearsOfExperience")}
                  error={errors.yearsOfExperience}
                />
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-text-primary">
                  Expected Salary (LPA) <span className="text-error">*</span>
                </label>
                <Input
                  placeholder="35"
                  value={form.expectedSalary}
                  onChange={update("expectedSalary")}
                  error={errors.expectedSalary}
                />
              </div>

              <div className="sm:col-span-2">
                <label className="mb-1.5 block text-sm font-medium text-text-primary">
                  LinkedIn URL{" "}
                  <span className="text-text-muted font-normal">(optional)</span>
                </label>
                <Input
                  type="url"
                  placeholder="https://linkedin.com/in/yourname"
                  value={form.linkedinUrl}
                  onChange={update("linkedinUrl")}
                />
              </div>
            </div>

            <Button onClick={goNext} size="lg" className="w-full mt-1">
              Continue to Resume
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Step 2 — Resume Upload */}
      {currentStep === 2 && (
        <Card>
          <CardContent className="p-6 flex flex-col gap-5">
            <div>
              <h2 className="text-base font-semibold text-text-primary">Upload Your Resume</h2>
              <p className="text-xs text-text-muted mt-0.5">
                Our AI will parse your resume to match it with the job requirements
              </p>
            </div>

            {/* Drop zone */}
            <div
              onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
              onDragLeave={() => setDragActive(false)}
              onDrop={handleDrop}
              onClick={() => !resumeFile && fileInputRef.current?.click()}
              className={cn(
                "relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 text-center transition-colors duration-150",
                dragActive
                  ? "border-brand bg-brand-light"
                  : resumeFile
                  ? "border-brand bg-brand-light/50"
                  : "border-border bg-bg hover:border-brand/50 hover:bg-brand-light/30 cursor-pointer"
              )}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.doc,.docx"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFile(file);
                }}
              />

              {resumeFile ? (
                <div className="flex flex-col items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand/10">
                    <FileText className="h-6 w-6 text-brand" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-text-primary">{resumeFile.name}</p>
                    <p className="text-xs text-text-muted mt-0.5">
                      {(resumeFile.size / 1024).toFixed(0)} KB
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setResumeFile(null);
                      if (fileInputRef.current) fileInputRef.current.value = "";
                    }}
                    className="inline-flex items-center gap-1.5 text-xs text-error hover:underline"
                  >
                    <X className="h-3 w-3" />
                    Remove file
                  </button>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-light">
                    <Upload className="h-6 w-6 text-brand" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-text-primary">
                      {dragActive ? "Drop your resume here" : "Drag & drop your resume"}
                    </p>
                    <p className="text-xs text-text-muted mt-1">
                      or{" "}
                      <span className="text-brand font-medium">click to browse</span>
                      {" "}— PDF or DOCX, max 10 MB
                    </p>
                  </div>
                </div>
              )}
            </div>

            {errors.resume && (
              <p className="text-xs text-error">{errors.resume}</p>
            )}

            <div className="flex gap-3">
              <Button
                variant="secondary"
                size="lg"
                className="flex-1"
                onClick={() => setCurrentStep(1)}
              >
                Back
              </Button>
              <Button size="lg" className="flex-1" onClick={goNext}>
                Review & Submit
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3 — Review & Submit */}
      {currentStep === 3 && (
        <Card>
          <CardContent className="p-6 flex flex-col gap-5">
            <div>
              <h2 className="text-base font-semibold text-text-primary">Review Your Application</h2>
              <p className="text-xs text-text-muted mt-0.5">
                Double-check your information before submitting
              </p>
            </div>

            {/* Summary */}
            <div className="rounded-lg border border-border bg-bg p-4 flex flex-col gap-3 text-sm">
              <Row label="Full Name" value={form.fullName} />
              <Row label="Email" value={form.email} />
              <Row label="Phone" value={form.phone} />
              {form.currentRole && <Row label="Current Role" value={form.currentRole} />}
              {form.currentCompany && <Row label="Current Company" value={form.currentCompany} />}
              <Row label="Experience" value={`${form.yearsOfExperience} years`} />
              <Row label="Expected Salary" value={`₹${form.expectedSalary} LPA`} />
              {form.linkedinUrl && <Row label="LinkedIn" value={form.linkedinUrl} />}
            </div>

            {/* Resume */}
            {resumeFile && (
              <div className="flex items-center gap-3 rounded-lg border border-border bg-bg p-3">
                <FileText className="h-5 w-5 text-brand shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary truncate">{resumeFile.name}</p>
                  <p className="text-xs text-text-muted">{(resumeFile.size / 1024).toFixed(0)} KB</p>
                </div>
                <Check className="h-4 w-4 text-success shrink-0" />
              </div>
            )}

            <p className="text-xs text-text-muted leading-relaxed">
              By submitting, you agree to NexusAI Talent OS processing your application data.
              We&apos;ll review your application and get back within 24 hours.
            </p>

            <div className="flex gap-3">
              <Button
                variant="secondary"
                size="lg"
                className="flex-1"
                onClick={() => setCurrentStep(2)}
              >
                Back
              </Button>
              <Button
                size="lg"
                className="flex-1"
                loading={submitting}
                onClick={handleSubmit}
              >
                Submit Application
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="text-text-muted shrink-0">{label}</span>
      <span className="text-text-primary font-medium text-right break-all">{value}</span>
    </div>
  );
}
