"use client";

import Link from "next/link";
import Image from "next/image";
import { useTheme } from "@/hooks/useTheme";
import {
  Briefcase,
  Brain,
  Video,
  FileText,
  Mic,
  Star,
  ShieldCheck,
  BarChart3,
  ArrowRight,
  CheckCircle2,
  Play,
  ChevronRight,
  Twitter,
  Linkedin,
  Github,
  TrendingUp,
  Clock,
  DollarSign,
  Award,
} from "lucide-react";
import PublicNav from "@/components/layout/public-nav";
import { cn } from "@/lib/utils";

// ─── Data ────────────────────────────────────────────────────────────────────

const STATS = [
  { value: "10,000+", label: "Interviews Conducted", icon: Video },
  { value: "95%", label: "Completion Rate", icon: Award },
  { value: "3x", label: "Faster Hiring", icon: Clock },
  { value: "50%", label: "Cost Reduction", icon: DollarSign },
];

const HOW_IT_WORKS = [
  {
    step: "01",
    icon: Briefcase,
    title: "Post a Job",
    description:
      "Create a job listing with required skills, experience, and configure multi-round interview flow in minutes.",
  },
  {
    step: "02",
    icon: Brain,
    title: "AI Screens Candidates",
    description:
      "AI parses every resume, scores skills overlap against your JD, and auto-shortlists qualified candidates.",
  },
  {
    step: "03",
    icon: Video,
    title: "AI Conducts Interviews",
    description:
      "Voice AI interviews each shortlisted candidate across Introduction, Technical, Behavioral, and HR rounds.",
  },
  {
    step: "04",
    icon: FileText,
    title: "Get Actionable Reports",
    description:
      "Receive detailed assessments with per-skill scores, hire recommendation, and salary guidance as a PDF.",
  },
];

const FEATURES = [
  {
    icon: Brain,
    title: "Resume Intelligence",
    description:
      "GPT-4o parses resumes and scores candidates against job requirements across skills, experience, and education.",
  },
  {
    icon: Video,
    title: "Multi-Round Interviews",
    description:
      "Introduction, Technical, Behavioral, and HR rounds — all fully automated and customizable per role.",
  },
  {
    icon: Mic,
    title: "Voice AI Interviewer",
    description:
      "Natural speech-to-speech conversation powered by OpenAI Realtime API. Sounds human, scales infinitely.",
  },
  {
    icon: Star,
    title: "Real-Time Evaluation",
    description:
      "Each answer is scored live on 5 dimensions: relevance, depth, accuracy, communication, and confidence.",
  },
  {
    icon: ShieldCheck,
    title: "Smart Proctoring",
    description:
      "Client-side face detection monitors presence and integrity throughout every interview session.",
  },
  {
    icon: BarChart3,
    title: "Assessment Reports",
    description:
      "Comprehensive PDF reports with per-skill breakdowns, strengths, weaknesses, and hiring recommendations.",
  },
];

const PRICING = [
  {
    name: "Starter",
    price: "$500",
    period: "/month",
    description: "Perfect for early-stage teams starting to automate hiring.",
    popular: false,
    features: [
      "50 AI interviews per month",
      "2 interview rounds",
      "Resume parsing & screening",
      "Text-based assessment reports",
      "Email notifications",
      "Candidate portal",
    ],
    cta: "Start Free Trial",
    ctaVariant: "outline" as const,
  },
  {
    name: "Pro",
    price: "$2,000",
    period: "/month",
    description: "For growing teams that need full pipeline automation.",
    popular: true,
    features: [
      "200 AI interviews per month",
      "All 4 interview rounds",
      "Adaptive question generation",
      "Video proctoring + integrity score",
      "PDF assessment reports",
      "Priority support",
    ],
    cta: "Start Free Trial",
    ctaVariant: "primary" as const,
  },
  {
    name: "Enterprise",
    price: "$5,000+",
    period: " setup",
    description: "Custom deployment for large-scale hiring operations.",
    popular: false,
    features: [
      "Unlimited interviews",
      "Custom scoring rubrics",
      "ATS integration (Greenhouse, Lever)",
      "White-label & API access",
      "Dedicated account manager",
      "SLA + custom data retention",
    ],
    cta: "Contact Sales",
    ctaVariant: "outline" as const,
  },
];

const FOOTER_LINKS = [
  {
    heading: "Product",
    links: ["Features", "How It Works", "Pricing", "Security", "Changelog"],
  },
  {
    heading: "Company",
    links: ["About", "Blog", "Careers", "Press", "Contact"],
  },
  {
    heading: "Resources",
    links: ["Documentation", "API Reference", "Case Studies", "Community"],
  },
  {
    heading: "Legal",
    links: ["Privacy Policy", "Terms of Service", "Cookie Policy", "GDPR"],
  },
];

// ─── Sub-components ───────────────────────────────────────────────────────────

function DashboardMockup() {
  return (
    <div className="relative w-full max-w-2xl mx-auto">
      {/* Glow behind the card */}
      <div className="absolute inset-0 -z-10 bg-brand/10 blur-3xl rounded-3xl" />

      <div className="rounded-xl border border-border bg-surface shadow-xl overflow-hidden">
        {/* Fake browser chrome */}
        <div className="flex items-center gap-2 px-4 py-3 bg-bg border-b border-border">
          <div className="flex gap-1.5">
            <span className="h-3 w-3 rounded-full bg-red-400" />
            <span className="h-3 w-3 rounded-full bg-yellow-400" />
            <span className="h-3 w-3 rounded-full bg-green-400" />
          </div>
          <div className="flex-1 mx-3 h-6 rounded-full bg-border flex items-center px-3">
            <span className="text-xs text-text-muted">app.nexusai-talent-os.com/admin/dashboard</span>
          </div>
        </div>

        {/* Dashboard content */}
        <div className="p-5 bg-bg">
          {/* Stats row */}
          <div className="grid grid-cols-4 gap-3 mb-4">
            {[
              { label: "Active Jobs", value: "12" },
              { label: "Candidates", value: "284" },
              { label: "Interviews Today", value: "8" },
              { label: "Avg Score", value: "76" },
            ].map((stat) => (
              <div key={stat.label} className="bg-surface rounded-lg border border-border p-3 text-center">
                <p className="text-lg font-bold text-text-primary">{stat.value}</p>
                <p className="text-[11px] text-text-muted mt-0.5">{stat.label}</p>
              </div>
            ))}
          </div>

          {/* Candidate rows */}
          <div className="bg-surface rounded-lg border border-border overflow-hidden">
            <div className="px-4 py-2.5 border-b border-border flex items-center justify-between">
              <span className="text-xs font-semibold text-text-primary">Recent Interviews</span>
              <span className="text-xs text-brand font-medium">View all</span>
            </div>
            {[
              { name: "Priya Singh", role: "Senior Engineer", score: 88, badge: "Strong Hire", badgeColor: "bg-success/10 text-success" },
              { name: "Rahul Kumar", role: "Product Manager", score: 74, badge: "Hire", badgeColor: "bg-brand-light text-brand" },
              { name: "Ananya Mehta", role: "Data Scientist", score: 61, badge: "Maybe", badgeColor: "bg-warning-light text-warning" },
            ].map((c) => (
              <div key={c.name} className="flex items-center gap-3 px-4 py-3 border-b border-border last:border-0 hover:bg-bg transition-colors duration-100">
                <div className="h-8 w-8 rounded-full bg-brand flex items-center justify-center text-white text-xs font-semibold shrink-0">
                  {c.name.split(" ").map((n) => n[0]).join("")}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary truncate">{c.name}</p>
                  <p className="text-xs text-text-muted truncate">{c.role}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-text-primary">{c.score}</span>
                  <span className={cn("text-[10px] font-semibold px-2 py-0.5 rounded-full", c.badgeColor)}>
                    {c.badge}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Interview rounds visual */}
          <div className="mt-3 bg-surface rounded-lg border border-border p-3">
            <p className="text-xs font-semibold text-text-muted mb-2.5">ACTIVE INTERVIEW — Arjun Sharma</p>
            <div className="flex items-center gap-1.5">
              {["Intro", "Technical", "Behavioral", "HR"].map((round, i) => (
                <div key={round} className="flex items-center gap-1.5">
                  <div className={cn(
                    "flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium",
                    i === 1
                      ? "bg-brand text-white"
                      : i < 1
                      ? "bg-success/10 text-success"
                      : "bg-bg text-text-muted border border-border"
                  )}>
                    {i < 1 && <CheckCircle2 className="h-3 w-3" />}
                    {round}
                  </div>
                  {i < 3 && <ChevronRight className="h-3 w-3 text-text-muted shrink-0" />}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StepConnector() {
  return (
    <div className="hidden lg:flex items-center justify-center w-12 shrink-0">
      <div className="flex items-center gap-1">
        <div className="h-px w-4 bg-border" />
        <ArrowRight className="h-4 w-4 text-text-muted" />
        <div className="h-px w-4 bg-border" />
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  const { theme } = useTheme();

  return (
    <div className="min-h-screen bg-surface">
      <PublicNav />

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden bg-surface">
        {/* Subtle dot grid background */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "radial-gradient(circle, #0A66C2 1px, transparent 1px)",
            backgroundSize: "28px 28px",
          }}
        />
        {/* Brand gradient blob */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 h-96 w-[600px] rounded-full bg-brand/8 blur-3xl" />

        <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pt-20 pb-24 lg:pt-28 lg:pb-32">
          <div className="flex flex-col lg:flex-row items-center gap-16 lg:gap-20">
            {/* Left — copy */}
            <div className="flex-1 text-center lg:text-left max-w-xl">
              {/* Pill badge */}
              <div className="inline-flex items-center gap-2 rounded-full border border-brand/20 bg-brand-light px-3.5 py-1.5 mb-6">
                <TrendingUp className="h-3.5 w-3.5 text-brand" />
                <span className="text-xs font-semibold text-brand tracking-wide uppercase">
                  AI-Powered Hiring Platform
                </span>
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-[52px] font-bold text-text-primary leading-[1.1] tracking-tight text-balance">
                Hire Smarter with{" "}
                <span className="text-brand">AI-Powered</span>{" "}
                Interviews
              </h1>

              <p className="mt-5 text-lg text-text-muted leading-relaxed text-balance">
                Automate your entire hiring pipeline — from resume screening to
                multi-round AI interviews — and make data-driven hiring decisions
                in minutes, not weeks.
              </p>

              <div className="mt-8 flex flex-col sm:flex-row items-center gap-3 lg:justify-start justify-center">
                <Link
                  href="/signup"
                  className="inline-flex items-center justify-center gap-2 rounded-full bg-brand px-6 py-3 text-sm font-semibold text-white hover:bg-brand-hover transition-colors duration-100 shadow-sm"
                >
                  Start Free Trial
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <button className="inline-flex items-center justify-center gap-2 rounded-full border border-border bg-surface px-6 py-3 text-sm font-semibold text-text-primary hover:bg-bg hover:border-brand/30 transition-colors duration-100">
                  <Play className="h-4 w-4 fill-brand text-brand" />
                  Watch Demo
                </button>
              </div>

              {/* Social proof micro */}
              <p className="mt-6 text-xs text-text-muted">
                Trusted by{" "}
                <span className="font-semibold text-text-primary">500+</span>{" "}
                hiring teams worldwide. No credit card required.
              </p>
            </div>

            {/* Right — dashboard mockup */}
            <div className="flex-1 w-full lg:max-w-[580px]">
              <DashboardMockup />
            </div>
          </div>
        </div>
      </section>

      {/* ── Stats bar ────────────────────────────────────────────────────── */}
      <section className="border-y border-border bg-bg">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-0 lg:divide-x lg:divide-border">
            {STATS.map(({ value, label, icon: Icon }) => (
              <div key={label} className="flex flex-col items-center text-center gap-2 lg:px-8">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-light">
                  <Icon className="h-5 w-5 text-brand" />
                </div>
                <p className="text-3xl font-bold text-text-primary">{value}</p>
                <p className="text-sm text-text-muted">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────────────── */}
      <section id="how-it-works" className="bg-surface py-20 lg:py-28">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14">
            <p className="text-sm font-semibold text-brand uppercase tracking-widest mb-3">
              How It Works
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold text-text-primary tracking-tight">
              From application to hire in 4 steps
            </h2>
            <p className="mt-4 text-text-muted max-w-xl mx-auto text-base leading-relaxed">
              NexusAI Talent OS handles the entire process — you just review the final
              recommendation and make the call.
            </p>
          </div>

          <div className="flex flex-col lg:flex-row items-start lg:items-stretch gap-0">
            {HOW_IT_WORKS.map((step, index) => (
              <div key={step.step} className="flex flex-col lg:flex-row items-start flex-1">
                {/* Step card */}
                <div className="group flex flex-col gap-4 p-6 rounded-xl border border-border bg-surface hover:border-brand/30 hover:bg-brand-light/20 transition-all duration-150 w-full">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-light group-hover:bg-brand/15 transition-colors duration-150">
                      <step.icon className="h-5 w-5 text-brand" />
                    </div>
                    <span className="text-xs font-bold text-brand/50 tracking-widest">
                      STEP {step.step}
                    </span>
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-text-primary mb-1.5">
                      {step.title}
                    </h3>
                    <p className="text-sm text-text-muted leading-relaxed">
                      {step.description}
                    </p>
                  </div>
                </div>
                {/* Connector */}
                {index < HOW_IT_WORKS.length - 1 && <StepConnector />}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features grid ────────────────────────────────────────────────── */}
      <section id="features" className="bg-bg py-20 lg:py-28">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14">
            <p className="text-sm font-semibold text-brand uppercase tracking-widest mb-3">
              Platform Features
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold text-text-primary tracking-tight">
              Everything you need to hire with confidence
            </h2>
            <p className="mt-4 text-text-muted max-w-xl mx-auto text-base leading-relaxed">
              Purpose-built for modern hiring teams who need speed, accuracy,
              and fairness at scale.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map(({ icon: Icon, title, description }) => (
              <div
                key={title}
                className="group flex flex-col gap-4 rounded-xl border border-border bg-surface p-6 hover:border-brand/30 hover:shadow-sm transition-all duration-150"
              >
                <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-brand-light group-hover:bg-brand/15 transition-colors duration-150">
                  <Icon className="h-5 w-5 text-brand" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-text-primary mb-1.5">
                    {title}
                  </h3>
                  <p className="text-sm text-text-muted leading-relaxed">
                    {description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ──────────────────────────────────────────────────────── */}
      <section id="pricing" className="bg-surface py-20 lg:py-28">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14">
            <p className="text-sm font-semibold text-brand uppercase tracking-widest mb-3">
              Pricing
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold text-text-primary tracking-tight">
              Simple, transparent pricing
            </h2>
            <p className="mt-4 text-text-muted max-w-md mx-auto text-base leading-relaxed">
              No per-seat fees. No hidden charges. Pay for the interviews you
              run.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-5 max-w-5xl mx-auto items-start">
            {PRICING.map((plan) => (
              <div
                key={plan.name}
                className={cn(
                  "relative flex flex-col rounded-xl border p-7 transition-all duration-150",
                  plan.popular
                    ? "border-brand shadow-lg shadow-brand/10 bg-surface ring-1 ring-brand/20"
                    : "border-border bg-surface hover:border-brand/20"
                )}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="inline-flex items-center rounded-full bg-brand px-3 py-1 text-[11px] font-bold text-white uppercase tracking-wider">
                      Most Popular
                    </span>
                  </div>
                )}

                <div className="mb-5">
                  <h3 className="text-base font-semibold text-text-primary">
                    {plan.name}
                  </h3>
                  <p className="text-sm text-text-muted mt-1">{plan.description}</p>
                </div>

                <div className="mb-6 flex items-end gap-1">
                  <span className="text-4xl font-bold text-text-primary">
                    {plan.price}
                  </span>
                  <span className="text-sm text-text-muted mb-1.5">{plan.period}</span>
                </div>

                <ul className="flex flex-col gap-2.5 mb-8 flex-1">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2.5">
                      <CheckCircle2 className="h-4 w-4 text-brand shrink-0 mt-0.5" />
                      <span className="text-sm text-text-muted">{feature}</span>
                    </li>
                  ))}
                </ul>

                <Link
                  href={plan.name === "Enterprise" ? "/contact" : "/signup"}
                  className={cn(
                    "inline-flex items-center justify-center rounded-full px-5 py-2.5 text-sm font-semibold transition-colors duration-100",
                    plan.ctaVariant === "primary"
                      ? "bg-brand text-white hover:bg-brand-hover"
                      : "border border-brand text-brand hover:bg-brand-light"
                  )}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden bg-brand py-20 lg:py-28">
        {/* Subtle pattern */}
        <div
          className="absolute inset-0 opacity-[0.06]"
          style={{
            backgroundImage:
              "radial-gradient(circle, white 1px, transparent 1px)",
            backgroundSize: "24px 24px",
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-br from-brand via-brand to-brand-hover" />

        <div className="relative mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
            Ready to Transform Your Hiring?
          </h2>
          <p className="mt-4 text-lg text-white/75 leading-relaxed">
            Join 500+ hiring teams using NexusAI Talent OS to run faster, fairer, and
            smarter interviews at scale.
          </p>

          <form className="mt-10 flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
            <input
              type="email"
              placeholder="Enter your work email"
              className="flex-1 h-12 rounded-full border border-white/20 bg-white/10 px-5 text-sm text-white placeholder:text-white/50 focus:outline-none focus:border-white/50 focus:bg-white/15 transition-all duration-100"
            />
            <button
              type="submit"
              className="h-12 shrink-0 inline-flex items-center justify-center gap-2 rounded-full bg-white px-6 text-sm font-semibold text-brand hover:bg-white/90 transition-colors duration-100"
            >
              Get Started
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>

          <p className="mt-4 text-sm text-white/50">
            Free trial. No credit card required. Setup in 5 minutes.
          </p>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer className="bg-surface border-t border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pt-14 pb-10">
          <div className="grid grid-cols-2 md:grid-cols-6 gap-8 lg:gap-12">
            {/* Brand column */}
            <div className="col-span-2">
              <div className="mb-4">
                <Image
                  src={theme === "dark" ? "/logo.png" : "/logo_full.png"}
                  alt="Talent OS Logo"
                  width={80}
                  height={80}
                  className="object-contain"
                />
              </div>
              <p className="text-sm text-text-muted leading-relaxed max-w-xs">
                AI-powered interview platform that automates the entire hiring
                pipeline from screening to final recommendation.
              </p>
              {/* Social icons */}
              <div className="flex items-center gap-3 mt-5">
                {[Twitter, Linkedin, Github].map((Icon, i) => (
                  <a
                    key={i}
                    href="#"
                    className="flex h-8 w-8 items-center justify-center rounded-full border border-border text-text-muted hover:text-brand hover:border-brand/30 transition-colors duration-100"
                    aria-label="Social link"
                  >
                    <Icon className="h-4 w-4" />
                  </a>
                ))}
              </div>
            </div>

            {/* Link columns */}
            {FOOTER_LINKS.map((col) => (
              <div key={col.heading}>
                <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider mb-4">
                  {col.heading}
                </h4>
                <ul className="flex flex-col gap-2.5">
                  {col.links.map((link) => (
                    <li key={link}>
                      <a
                        href="#"
                        className="text-sm text-text-muted hover:text-text-primary transition-colors duration-100"
                      >
                        {link}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="mt-12 pt-6 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-3">
            <p className="text-sm text-text-muted">
              &copy; 2026 NexusAI Talent OS. All rights reserved.
            </p>
            <p className="text-xs text-text-muted">
              Built with AI. Trusted by hiring teams worldwide.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
