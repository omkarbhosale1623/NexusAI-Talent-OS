import Link from "next/link";
import { notFound } from "next/navigation";
import {
  ArrowLeft,
  MapPin,
  Briefcase,
  Clock,
  IndianRupee,
  GraduationCap,
  MessageSquare,
  Users,
  Handshake,
  Code2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// ─── Mock data ───────────────────────────────────────────────────────────────

type JobType = "Remote" | "Hybrid" | "Onsite";

interface InterviewRound {
  name: string;
  duration: string;
  description: string;
  icon: React.ReactNode;
}

interface JobDetail {
  id: string;
  title: string;
  department: string;
  location: string;
  type: JobType;
  experience: string;
  skills: string[];
  salaryMin: number;
  salaryMax: number;
  postedDaysAgo: number;
  description: string;
  responsibilities: string[];
  requirements: string[];
}

const MOCK_JOBS: Record<string, JobDetail> = {
  "1": {
    id: "1",
    title: "Senior Full-Stack Engineer",
    department: "Engineering",
    location: "Bangalore, IN",
    type: "Hybrid",
    experience: "4–7 years",
    skills: ["React", "Node.js", "TypeScript", "PostgreSQL", "Redis", "Docker", "AWS"],
    salaryMin: 30,
    salaryMax: 50,
    postedDaysAgo: 2,
    description:
      "We're looking for a Senior Full-Stack Engineer to join our product engineering team. You'll own features end-to-end — from designing APIs to shipping pixel-perfect UIs. We move fast, ship frequently, and care deeply about code quality and user experience.",
    responsibilities: [
      "Design and implement scalable REST APIs using Node.js and FastAPI",
      "Build responsive, accessible front-end features with React and TypeScript",
      "Collaborate with product and design on feature specifications",
      "Write comprehensive tests and conduct code reviews",
      "Participate in on-call rotation and incident response",
    ],
    requirements: [
      "4+ years of professional full-stack development experience",
      "Strong proficiency in React, TypeScript, and Node.js",
      "Experience with PostgreSQL, query optimization, and migrations",
      "Familiarity with Docker and cloud deployments (AWS or GCP)",
      "Strong communication and cross-functional collaboration skills",
    ],
  },
  "2": {
    id: "2",
    title: "AI/ML Engineer",
    department: "AI Research",
    location: "Remote",
    type: "Remote",
    experience: "3–6 years",
    skills: ["Python", "PyTorch", "LangChain", "OpenAI API", "FastAPI", "pgvector"],
    salaryMin: 35,
    salaryMax: 60,
    postedDaysAgo: 1,
    description:
      "Join our AI research team to build the intelligence layer of NexusAI Talent OS. You'll design and implement LLM pipelines, adaptive question generation, and per-answer evaluation engines that power AI-driven interviews for thousands of candidates.",
    responsibilities: [
      "Build and maintain LLM pipelines using LangChain and OpenAI APIs",
      "Design adaptive question generation and evaluation rubrics",
      "Implement RAG systems with pgvector for resume-JD matching",
      "Monitor AI costs, latency, and quality in production",
      "Experiment with new models and publish internal findings",
    ],
    requirements: [
      "3+ years building production ML/AI systems",
      "Strong Python, PyTorch or TensorFlow proficiency",
      "Hands-on experience with LLMs, embeddings, and RAG pipelines",
      "Familiarity with FastAPI and async Python",
      "Experience evaluating and fine-tuning language models",
    ],
  },
  "3": {
    id: "3",
    title: "Product Designer",
    department: "Design",
    location: "Mumbai, IN",
    type: "Onsite",
    experience: "3–5 years",
    skills: ["Figma", "User Research", "Prototyping", "Design Systems", "Accessibility"],
    salaryMin: 20,
    salaryMax: 35,
    postedDaysAgo: 5,
    description:
      "We're seeking a Product Designer to shape the candidate and recruiter experience on NexusAI Talent OS. You'll work closely with engineering and product to design flows that are intuitive, accessible, and delightful — from job listings to live AI interview rooms.",
    responsibilities: [
      "Own end-to-end design for new features from discovery to delivery",
      "Conduct user research and synthesize findings into product decisions",
      "Maintain and evolve the NexusAI Talent OS design system",
      "Create high-fidelity prototypes for usability testing",
      "Partner with engineers to ensure accurate implementation",
    ],
    requirements: [
      "3+ years of product design experience at a SaaS company",
      "Expert-level Figma proficiency including auto-layout and components",
      "Experience conducting usability tests and user interviews",
      "Strong portfolio demonstrating end-to-end product thinking",
      "Knowledge of accessibility standards (WCAG 2.1)",
    ],
  },
  "4": {
    id: "4",
    title: "DevOps Engineer",
    department: "Infrastructure",
    location: "Remote",
    type: "Remote",
    experience: "3–6 years",
    skills: ["AWS", "Docker", "Kubernetes", "Terraform", "CI/CD", "Linux", "Grafana"],
    salaryMin: 25,
    salaryMax: 45,
    postedDaysAgo: 3,
    description:
      "Help us build and maintain the infrastructure that powers NexusAI Talent OS's real-time AI interview platform. You'll own cloud architecture, CI/CD pipelines, observability, and reliability — ensuring a seamless experience for candidates and recruiters worldwide.",
    responsibilities: [
      "Manage AWS infrastructure using Terraform and IaC best practices",
      "Build and maintain CI/CD pipelines with GitHub Actions",
      "Configure and maintain Kubernetes clusters for production workloads",
      "Implement monitoring, alerting, and incident response processes",
      "Drive cost optimization and performance improvements",
    ],
    requirements: [
      "3+ years of DevOps/Platform engineering experience",
      "Deep AWS expertise (ECS, RDS, CloudFront, S3, ALB)",
      "Strong Terraform skills and IaC mindset",
      "Experience with Kubernetes and container orchestration",
      "Familiarity with observability stacks (Prometheus, Grafana, Loki)",
    ],
  },
  "5": {
    id: "5",
    title: "Backend Engineer — Python",
    department: "Engineering",
    location: "Pune, IN",
    type: "Hybrid",
    experience: "2–5 years",
    skills: ["Python", "FastAPI", "PostgreSQL", "Celery", "Redis", "Pydantic"],
    salaryMin: 22,
    salaryMax: 40,
    postedDaysAgo: 7,
    description:
      "Join our backend team to build the APIs and services that power NexusAI Talent OS's hiring pipeline — from resume parsing to interview scheduling and evaluation. You'll work on high-throughput async Python services that handle thousands of real-time events.",
    responsibilities: [
      "Build and maintain FastAPI services for the hiring pipeline",
      "Design and optimize PostgreSQL schemas and queries",
      "Implement async background workers with Celery and Redis",
      "Write comprehensive unit and integration tests",
      "Participate in architecture discussions and code reviews",
    ],
    requirements: [
      "2+ years of professional Python backend development",
      "Experience with FastAPI or Django/Flask",
      "Strong PostgreSQL skills including query optimization",
      "Familiarity with message queues (Celery, Redis, or RabbitMQ)",
      "Good understanding of REST API design principles",
    ],
  },
  "6": {
    id: "6",
    title: "Growth Marketing Manager",
    department: "Marketing",
    location: "Delhi, IN",
    type: "Onsite",
    experience: "3–6 years",
    skills: ["SEO", "Paid Ads", "Analytics", "CRO", "HubSpot", "Google Ads"],
    salaryMin: 15,
    salaryMax: 28,
    postedDaysAgo: 10,
    description:
      "Drive NexusAI Talent OS's growth by owning acquisition channels, conversion funnels, and retention loops. You'll build and optimize the marketing engine that brings enterprise hiring teams to our platform.",
    responsibilities: [
      "Own SEO strategy and content marketing roadmap",
      "Manage paid acquisition across Google Ads and LinkedIn",
      "Build and optimize email nurture sequences in HubSpot",
      "Run A/B tests to improve landing page and signup conversion",
      "Report weekly on MQLs, CAC, and pipeline velocity to leadership",
    ],
    requirements: [
      "3+ years in B2B SaaS growth or demand generation",
      "Proven track record of driving MQL growth through SEO and paid",
      "Strong analytical skills and comfort with marketing analytics",
      "Experience with HubSpot, Google Analytics, and Google Ads",
      "Excellent writing skills for both copy and long-form content",
    ],
  },
};

const TYPE_BADGE: Record<JobType, "success" | "default" | "outline"> = {
  Remote: "success",
  Hybrid: "default",
  Onsite: "outline",
};

const INTERVIEW_ROUNDS: InterviewRound[] = [
  {
    name: "Introduction",
    duration: "5–7 min",
    description: "Get to know the role, your background, and why you're excited about this opportunity.",
    icon: <MessageSquare className="h-4 w-4 text-brand" />,
  },
  {
    name: "Technical",
    duration: "15–20 min",
    description: "Adaptive technical questions based on your resume skills and the role requirements.",
    icon: <Code2 className="h-4 w-4 text-brand" />,
  },
  {
    name: "Behavioral",
    duration: "10–15 min",
    description: "STAR-method questions on leadership, teamwork, conflict resolution, and ownership.",
    icon: <Users className="h-4 w-4 text-brand" />,
  },
  {
    name: "HR & Culture",
    duration: "5–10 min",
    description: "Salary expectations, availability, work preferences, and your questions for us.",
    icon: <Handshake className="h-4 w-4 text-brand" />,
  },
];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const job = MOCK_JOBS[id];

  if (!job) notFound();

  return (
    <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 py-10">
      {/* Back link */}
      <Link
        href="/jobs"
        className="inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-text-primary transition-colors mb-6"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to all positions
      </Link>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main content */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          {/* Title card */}
          <Card>
            <CardContent className="p-6">
              <h1 className="text-2xl font-bold text-text-primary">{job.title}</h1>

              {/* Tags row */}
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 text-sm text-text-muted">
                  <Briefcase className="h-4 w-4" />
                  {job.department}
                </span>
                <span className="text-border">·</span>
                <span className="inline-flex items-center gap-1.5 text-sm text-text-muted">
                  <MapPin className="h-4 w-4" />
                  {job.location}
                </span>
                <span className="text-border">·</span>
                <span className="inline-flex items-center gap-1.5 text-sm text-text-muted">
                  <GraduationCap className="h-4 w-4" />
                  {job.experience}
                </span>
                <span className="text-border">·</span>
                <span className="inline-flex items-center gap-1.5 text-sm text-text-muted">
                  <Clock className="h-4 w-4" />
                  Posted {job.postedDaysAgo}d ago
                </span>
              </div>

              {/* Type + salary */}
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <Badge variant={TYPE_BADGE[job.type]}>{job.type}</Badge>
                <span className="inline-flex items-center gap-0.5 text-sm font-semibold text-text-primary">
                  <IndianRupee className="h-3.5 w-3.5" />
                  {job.salaryMin}–{job.salaryMax} LPA
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Company info */}
          <Card>
            <CardContent className="p-6 flex items-center gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-brand text-white font-bold text-lg">
                H
              </div>
              <div>
                <p className="text-sm font-semibold text-text-primary">NexusAI Talent OS</p>
                <p className="text-xs text-text-muted mt-0.5">
                  AI-powered interview automation platform · Series A · 50–100 employees
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Description */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">About this role</CardTitle>
            </CardHeader>
            <CardContent className="pt-3">
              <p className="text-sm text-text-muted leading-relaxed">{job.description}</p>

              <h3 className="mt-5 text-sm font-semibold text-text-primary">Responsibilities</h3>
              <ul className="mt-2 flex flex-col gap-1.5">
                {job.responsibilities.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-text-muted">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
                    {item}
                  </li>
                ))}
              </ul>

              <h3 className="mt-5 text-sm font-semibold text-text-primary">Requirements</h3>
              <ul className="mt-2 flex flex-col gap-1.5">
                {job.requirements.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-text-muted">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
                    {item}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {/* Skills */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Required Skills</CardTitle>
            </CardHeader>
            <CardContent className="pt-3 flex flex-wrap gap-2">
              {job.skills.map((skill) => (
                <Badge key={skill} variant="outline">
                  {skill}
                </Badge>
              ))}
            </CardContent>
          </Card>

          {/* Interview process */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Interview Process</CardTitle>
            </CardHeader>
            <CardContent className="pt-3">
              <p className="text-xs text-text-muted mb-4">
                Our AI interviewer conducts all rounds automatically — total time 35–52 min.
              </p>
              <div className="flex flex-col gap-3">
                {INTERVIEW_ROUNDS.map((round, i) => (
                  <div key={round.name} className="flex items-start gap-3">
                    {/* Step number */}
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-light text-xs font-bold text-brand">
                      {i + 1}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        {round.icon}
                        <span className="text-sm font-semibold text-text-primary">
                          {round.name}
                        </span>
                        <span className="ml-auto text-xs text-text-muted">{round.duration}</span>
                      </div>
                      <p className="mt-0.5 text-xs text-text-muted leading-relaxed">
                        {round.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar CTA */}
        <div className="lg:col-span-1">
          <div className="sticky top-24">
            <Card>
              <CardContent className="p-6 flex flex-col gap-4">
                <div>
                  <p className="text-xs text-text-muted uppercase tracking-wide font-medium">Salary Range</p>
                  <p className="mt-1 text-xl font-bold text-text-primary">
                    ₹{job.salaryMin}–{job.salaryMax} LPA
                  </p>
                </div>

                <div className="h-px bg-border" />

                <div className="flex flex-col gap-2 text-sm text-text-muted">
                  <div className="flex justify-between">
                    <span>Location</span>
                    <span className="font-medium text-text-primary">{job.location}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Work type</span>
                    <span className="font-medium text-text-primary">{job.type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Experience</span>
                    <span className="font-medium text-text-primary">{job.experience}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Department</span>
                    <span className="font-medium text-text-primary">{job.department}</span>
                  </div>
                </div>

                <div className="h-px bg-border" />

                <Button asChild size="lg" className="w-full">
                  <Link href={`/jobs/${job.id}/apply`}>Apply for this Position</Link>
                </Button>

                <p className="text-center text-xs text-text-muted">
                  Takes ~5 min · AI interview scheduled after shortlisting
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
