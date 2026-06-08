import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface AgentCardProps {
  name: string;
  description: string;
  icon: LucideIcon;
  status?: "idle" | "running" | "ready";
  confidence?: number;
  className?: string;
}

const statusStyles = {
  idle: "bg-muted text-muted-foreground",
  running: "bg-violet-500/20 text-violet-300",
  ready: "bg-emerald-500/20 text-emerald-300",
};

export function AgentCard({
  name,
  description,
  icon: Icon,
  status = "ready",
  confidence,
  className,
}: AgentCardProps) {
  return (
    <div className={cn("glass rounded-xl p-5", className)}>
      <div className="flex items-start gap-3">
        <div className="rounded-lg border border-border bg-background/40 p-2">
          <Icon className="h-5 w-5 text-primary" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <h3 className="truncate font-semibold">{name}</h3>
            <span
              className={cn(
                "rounded-md px-2 py-0.5 text-[10px] uppercase tracking-wider",
                statusStyles[status],
              )}
            >
              {status}
            </span>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
          {confidence !== undefined && (
            <div className="mt-4">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Confidence</span>
                <span className="font-medium text-foreground">{confidence}%</span>
              </div>
              <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${confidence}%`, background: "var(--gradient-primary)" }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
