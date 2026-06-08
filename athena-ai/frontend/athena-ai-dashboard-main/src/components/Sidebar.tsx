import { Link, useRouterState } from "@tanstack/react-router";
import { LayoutDashboard, Activity, FileText, Bot, Settings, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

const items = [
  { to: "/app/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/app/events", icon: Activity, label: "Events" },
  { to: "/app/agents", icon: Bot, label: "AI Agents" },
  { to: "/app/reports", icon: FileText, label: "Reports" },
  { to: "/app/settings", icon: Settings, label: "Settings" },
] as const;

export function Sidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <aside className="hidden w-64 shrink-0 border-r border-sidebar-border bg-sidebar lg:flex lg:flex-col">
      <div className="flex h-16 items-center gap-2 border-b border-sidebar-border px-5">
        <div
          className="flex h-8 w-8 items-center justify-center rounded-lg"
          style={{ background: "var(--gradient-primary)" }}
        >
          <Sparkles className="h-4 w-4 text-background" />
        </div>
        <div>
          <div className="text-sm font-semibold tracking-tight">Athena AI</div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
            Decision Intelligence
          </div>
        </div>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {items.map((item) => {
          const active = pathname === item.to || pathname.startsWith(item.to + "/");
          return (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground",
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
              {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-primary" />}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-sidebar-border p-4">
        <div className="glass rounded-lg p-3">
          <p className="text-xs font-medium">System Online</p>
          <p className="mt-0.5 text-[10px] text-muted-foreground">All agents operational</p>
        </div>
      </div>
    </aside>
  );
}
