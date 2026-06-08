import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { KPICard } from "@/components/KPICard";
import { EventTable } from "@/components/EventTable";
import { WorkflowTimeline } from "@/components/WorkflowTimeline";
import { LoadingState } from "@/components/LoadingState";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { EventModal } from "@/components/EventModal";
import { Button } from "@/components/ui/button";
import { Activity, AlertTriangle, DollarSign, Gauge, Plus, RefreshCw } from "lucide-react";
import {
  AreaChart,
  Area,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useMemo, useState } from "react";

export const Route = createFileRoute("/app/dashboard")({
  component: Dashboard,
});

function Dashboard() {
  const [createOpen, setCreateOpen] = useState(false);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["events", { page: 1, page_size: 10 }],
    queryFn: () => api.listEvents({ page: 1, page_size: 10 }),
  });

  const stats = useMemo(() => {
    const items = data?.items ?? [];
    const critical = items.filter((e) => e.severity === "CRITICAL").length;
    const revenueRisk = items.reduce(
      (sum, e) => sum + (Number(e.metadata?.estimated_loss) || 0),
      0,
    );
    return {
      total: data?.total ?? items.length,
      critical,
      new: items.filter((e) => e.status === "NEW").length,
      processing: items.filter((e) => e.status === "PROCESSING").length,
      resolved: items.filter((e) => e.status === "RESOLVED").length,
      revenueRisk,
    };
  }, [data]);

  const trendData = useMemo(() => {
    const items = data?.items ?? [];
    return Array.from({ length: 7 }).map((_, index) => {
      const date = new Date();
      date.setDate(date.getDate() - (6 - index));
      const key = date.toISOString().slice(0, 10);
      const dayEvents = items.filter((event) => event.created_at?.startsWith(key));
      return {
        day: date.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
        risk: dayEvents.filter((event) => ["HIGH", "CRITICAL"].includes(event.severity)).length,
        resolved: dayEvents.filter((event) => event.status === "RESOLVED").length,
      };
    });
  }, [data]);

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Operational Command</h1>
          <p className="text-sm text-muted-foreground">Live signals across your environment.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="gap-2" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
          <Button onClick={() => setCreateOpen(true)} className="gap-2">
            <Plus className="h-4 w-4" /> Create Event
          </Button>
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KPICard title="Total Events" value={stats.total} icon={Activity} delta="all-time" />
        <KPICard
          title="Critical Events"
          value={stats.critical}
          icon={AlertTriangle}
          trend={stats.critical > 0 ? "down" : "up"}
          delta={stats.critical > 0 ? "Needs attention" : "All clear"}
        />
        <KPICard
          title="Revenue at Risk"
          value={`$${(stats.revenueRisk / 1000).toFixed(1)}k`}
          icon={DollarSign}
          delta="Estimated loss"
        />
        <KPICard
          title="Event Status"
          value={`${stats.new}/${stats.processing}/${stats.resolved}`}
          icon={Gauge}
          delta="New / Processing / Resolved"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="glass rounded-xl p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="font-semibold">Risk Trend</h3>
              <p className="text-xs text-muted-foreground">Last 14 operational windows</p>
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="risk" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="oklch(0.7 0.2 290)" stopOpacity={0.6} />
                    <stop offset="100%" stopColor="oklch(0.7 0.2 290)" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="resolved" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="oklch(0.74 0.17 200)" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="oklch(0.74 0.17 200)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="oklch(1 0 0 / 0.06)" />
                <XAxis dataKey="day" stroke="oklch(0.7 0.03 260)" fontSize={11} />
                <YAxis stroke="oklch(0.7 0.03 260)" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    background: "oklch(0.18 0.025 265)",
                    border: "1px solid oklch(1 0 0 / 0.1)",
                    borderRadius: 8,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="risk"
                  stroke="oklch(0.7 0.2 290)"
                  fill="url(#risk)"
                />
                <Area
                  type="monotone"
                  dataKey="resolved"
                  stroke="oklch(0.74 0.17 200)"
                  fill="url(#resolved)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        <WorkflowTimeline active={2} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-semibold">Recent Events</h3>
            <Link to="/app/events" className="text-sm text-primary hover:underline">
              View all
            </Link>
          </div>
          {isLoading ? (
            <LoadingState label="Loading events…" />
          ) : error ? (
            <ErrorState message={(error as Error).message} onRetry={() => refetch()} />
          ) : data && data.items.length > 0 ? (
            <EventTable events={data.items.slice(0, 6)} />
          ) : (
            <EmptyState
              title="No events yet"
              description="Create your first event to start the decision workflow."
              actionLabel="Create Event"
              onAction={() => setCreateOpen(true)}
            />
          )}
        </div>
        <div className="space-y-3">
          <h3 className="font-semibold">AI Recommendations</h3>
          <EmptyState
            title="No saved recommendations yet"
            description="Run the AI workflow from an event detail page. Persisted recommendations arrive in the next backend phase."
          />
        </div>
      </div>

      <EventModal mode="create" open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}
