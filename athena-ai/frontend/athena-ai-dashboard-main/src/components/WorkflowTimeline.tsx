import { Eye, Search, TrendingUp, Compass, Cpu, FileText, ArrowRight } from "lucide-react";

const stages = [
  { name: "Observer", icon: Eye },
  { name: "Investigation", icon: Search },
  { name: "Prediction", icon: TrendingUp },
  { name: "Strategy", icon: Compass },
  { name: "Decision", icon: Cpu },
  { name: "Report", icon: FileText },
];

export function WorkflowTimeline({ active = -1 }: { active?: number }) {
  return (
    <div className="glass rounded-xl p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-semibold">Agent Workflow</h3>
        <span className="text-xs text-muted-foreground">Event → Report</span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {stages.map((s, i) => (
          <div key={s.name} className="flex items-center gap-2">
            <div
              className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-xs ${
                i <= active
                  ? "border-primary/50 bg-primary/10 text-primary"
                  : "border-border bg-background/30 text-muted-foreground"
              }`}
            >
              <s.icon className="h-3.5 w-3.5" />
              {s.name}
            </div>
            {i < stages.length - 1 && <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />}
          </div>
        ))}
      </div>
    </div>
  );
}
