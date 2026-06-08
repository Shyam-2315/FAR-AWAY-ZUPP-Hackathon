import { createFileRoute } from "@tanstack/react-router";
import { AgentCard } from "@/components/AgentCard";
import { WorkflowTimeline } from "@/components/WorkflowTimeline";
import { Eye, Search, TrendingUp, Compass, Cpu, FileText } from "lucide-react";

export const Route = createFileRoute("/app/agents")({
  component: AgentsPage,
});

const agents = [
  {
    name: "Observer Agent",
    description: "Monitors event streams and detects anomalies in real time.",
    icon: Eye,
    status: "ready" as const,
    confidence: 96,
  },
  {
    name: "Investigation Agent",
    description: "Correlates events with historical context and external signals.",
    icon: Search,
    status: "ready" as const,
    confidence: 89,
  },
  {
    name: "Prediction Agent",
    description: "Forecasts business impact across revenue, SLA and cost.",
    icon: TrendingUp,
    status: "running" as const,
    confidence: 92,
  },
  {
    name: "Strategy Agent",
    description: "Generates mitigation paths with trade-off analysis.",
    icon: Compass,
    status: "ready" as const,
    confidence: 88,
  },
  {
    name: "Decision Engine",
    description: "Recommends actions, requests human approval for high-stakes calls.",
    icon: Cpu,
    status: "idle" as const,
    confidence: 84,
  },
  {
    name: "Reporting Agent",
    description: "Composes executive-ready reports and audit trails.",
    icon: FileText,
    status: "ready" as const,
    confidence: 95,
  },
];

function AgentsPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">AI Agents</h1>
        <p className="text-sm text-muted-foreground">
          The agentic team that runs Athena's decision pipeline.
        </p>
      </header>

      <WorkflowTimeline active={2} />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {agents.map((a) => (
          <AgentCard key={a.name} {...a} />
        ))}
      </div>
    </div>
  );
}
