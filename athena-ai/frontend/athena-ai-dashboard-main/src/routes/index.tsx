import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Sparkles,
  Brain,
  ShieldCheck,
  Activity,
  LineChart,
  FileText,
  UserCheck,
  Lock,
  ArrowRight,
  Truck,
  Factory,
  HeartPulse,
  Building2,
  Eye,
  Search,
  TrendingUp,
  Compass,
  Cpu,
} from "lucide-react";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/")({
  component: Landing,
});

const features = [
  {
    icon: Brain,
    title: "Multi-Agent AI Workflow",
    desc: "Observer, Investigator, Predictor, Strategist and Decision agents collaborate end-to-end.",
  },
  {
    icon: Activity,
    title: "Real-Time Risk Monitoring",
    desc: "Continuously scan signals across operations and surface anomalies the moment they emerge.",
  },
  {
    icon: LineChart,
    title: "Predictive Business Impact",
    desc: "Quantify revenue, SLA and cost impact before incidents escalate.",
  },
  {
    icon: FileText,
    title: "Executive Reports",
    desc: "Board-ready summaries auto-generated from every decision.",
  },
  {
    icon: UserCheck,
    title: "Human Approval Layer",
    desc: "High-stakes actions stay reviewable with full audit trails.",
  },
  {
    icon: Lock,
    title: "Enterprise Security",
    desc: "Role-based access, encrypted secrets, and SOC-friendly logging.",
  },
];

const useCases = [
  {
    icon: Truck,
    title: "Logistics",
    desc: "Predict shipment delays, reroute fleets, protect SLAs.",
  },
  {
    icon: Factory,
    title: "Manufacturing",
    desc: "Detect line anomalies and contain downtime within minutes.",
  },
  {
    icon: HeartPulse,
    title: "Healthcare",
    desc: "Triage operational risks across networks and devices.",
  },
  {
    icon: Building2,
    title: "Smart City",
    desc: "Coordinate incidents across infrastructure in real time.",
  },
];

const stages = [
  { name: "Event", icon: Sparkles },
  { name: "Observer", icon: Eye },
  { name: "Investigation", icon: Search },
  { name: "Prediction", icon: TrendingUp },
  { name: "Strategy", icon: Compass },
  { name: "Decision", icon: Cpu },
  { name: "Report", icon: FileText },
];

function Landing() {
  return (
    <div className="min-h-screen">
      {/* Nav */}
      <header className="sticky top-0 z-30 border-b border-border/60 bg-background/60 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 lg:px-8">
          <Link to="/" className="flex items-center gap-2">
            <div
              className="flex h-8 w-8 items-center justify-center rounded-lg"
              style={{ background: "var(--gradient-primary)" }}
            >
              <Sparkles className="h-4 w-4 text-background" />
            </div>
            <span className="font-semibold tracking-tight">Athena AI</span>
          </Link>
          <nav className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
            <a href="#features" className="hover:text-foreground">
              Features
            </a>
            <a href="#architecture" className="hover:text-foreground">
              Architecture
            </a>
            <a href="#use-cases" className="hover:text-foreground">
              Use cases
            </a>
          </nav>
          <div className="flex items-center gap-2">
            <Link to="/login">
              <Button variant="ghost" size="sm">
                Login
              </Button>
            </Link>
            <Link to="/register">
              <Button size="sm">Get Started</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden bg-grid">
        <div
          className="pointer-events-none absolute inset-0"
          style={{ background: "var(--gradient-hero)" }}
        />
        <div className="relative mx-auto max-w-7xl px-4 py-24 text-center lg:px-8 lg:py-32">
          <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-border bg-background/40 px-3 py-1 text-xs text-muted-foreground backdrop-blur">
            <ShieldCheck className="h-3.5 w-3.5 text-primary" />
            Multi-agent decision intelligence
          </div>
          <h1 className="mx-auto mt-6 max-w-4xl text-5xl font-semibold tracking-tight md:text-6xl">
            Autonomous Decision Intelligence for{" "}
            <span className="text-gradient">Modern Operations</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-muted-foreground">
            Athena AI observes, investigates, predicts, decides, and reports in real time — so your
            teams act with confidence before incidents become losses.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link to="/register">
              <Button size="lg" className="gap-2">
                Get Started <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link to="/app/dashboard">
              <Button size="lg" variant="outline">
                View Demo
              </Button>
            </Link>
          </div>

          {/* Hero dashboard preview */}
          <div className="mx-auto mt-16 max-w-5xl">
            <div className="glass rounded-2xl p-2" style={{ boxShadow: "var(--shadow-elegant)" }}>
              <div className="rounded-xl border border-border bg-background/60 p-6">
                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                  {[
                    { l: "Total Events", v: "1,284" },
                    { l: "Critical", v: "17" },
                    { l: "Revenue at Risk", v: "$2.4M" },
                    { l: "Avg Confidence", v: "92%" },
                  ].map((k) => (
                    <div
                      key={k.l}
                      className="rounded-lg border border-border bg-background/40 p-4 text-left"
                    >
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                        {k.l}
                      </p>
                      <p className="mt-1 text-2xl font-semibold">{k.v}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-7xl px-4 py-20 lg:px-8">
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
            Built for high-stakes operations
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-muted-foreground">
            A control plane that brings every decision — and every reason behind it — into one view.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className="glass group rounded-xl p-6 transition hover:border-primary/40"
            >
              <div className="inline-flex rounded-lg border border-border bg-background/40 p-2 transition group-hover:border-primary/40">
                <f.icon className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mt-4 text-lg font-semibold">{f.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Architecture */}
      <section id="architecture" className="border-y border-border/60 bg-background/40">
        <div className="mx-auto max-w-7xl px-4 py-20 lg:px-8">
          <div className="mb-10 text-center">
            <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
              A six-stage agent pipeline
            </h2>
            <p className="mx-auto mt-3 max-w-2xl text-muted-foreground">
              From raw event to executive report — every step is explainable.
            </p>
          </div>
          <div className="glass overflow-x-auto rounded-2xl p-6">
            <div className="flex min-w-max items-center justify-between gap-3">
              {stages.map((s, i) => (
                <div key={s.name} className="flex items-center gap-3">
                  <div className="flex flex-col items-center gap-2">
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-primary/30 bg-primary/10">
                      <s.icon className="h-5 w-5 text-primary" />
                    </div>
                    <span className="text-xs text-muted-foreground">{s.name}</span>
                  </div>
                  {i < stages.length - 1 && (
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Use cases */}
      <section id="use-cases" className="mx-auto max-w-7xl px-4 py-20 lg:px-8">
        <div className="mb-10 text-center">
          <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
            Wherever operations get complex
          </h2>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {useCases.map((u) => (
            <div key={u.title} className="glass rounded-xl p-6">
              <u.icon className="h-6 w-6 text-primary" />
              <h3 className="mt-4 font-semibold">{u.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{u.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-7xl px-4 pb-20 lg:px-8">
        <div
          className="glass relative overflow-hidden rounded-2xl p-10 text-center"
          style={{ boxShadow: "var(--shadow-glow)" }}
        >
          <div
            className="pointer-events-none absolute inset-0 opacity-50"
            style={{ background: "var(--gradient-hero)" }}
          />
          <div className="relative">
            <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
              Bring Athena into your operations
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
              Spin up the dashboard and connect your event streams in minutes.
            </p>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              <Link to="/register">
                <Button size="lg">Create account</Button>
              </Link>
              <Link to="/login">
                <Button size="lg" variant="outline">
                  Login
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-border/60">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-4 py-8 text-sm text-muted-foreground md:flex-row lg:px-8">
          <div className="flex items-center gap-2">
            <div
              className="flex h-6 w-6 items-center justify-center rounded-md"
              style={{ background: "var(--gradient-primary)" }}
            >
              <Sparkles className="h-3 w-3 text-background" />
            </div>
            <span>© {new Date().getFullYear()} Athena AI</span>
          </div>
          <div className="flex items-center gap-4">
            <a href="#features" className="hover:text-foreground">
              Features
            </a>
            <a href="#architecture" className="hover:text-foreground">
              Architecture
            </a>
            <Link to="/login" className="hover:text-foreground">
              Login
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
