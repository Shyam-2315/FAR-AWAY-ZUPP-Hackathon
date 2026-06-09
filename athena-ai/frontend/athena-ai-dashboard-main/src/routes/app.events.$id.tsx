import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import {
  ArrowLeft,
  Compass,
  Cpu,
  Eye,
  FileText,
  Play,
  Search,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { ApiError, api, getApiErrorMessage } from "@/lib/api";
import type { AgentWorkflowResponse } from "@/lib/types";
import { SeverityBadge } from "@/components/SeverityBadge";
import { StatusBadge } from "@/components/StatusBadge";
import { WorkflowTimeline } from "@/components/WorkflowTimeline";
import { RecommendationCard } from "@/components/RecommendationCard";
import { ReportCard } from "@/components/ReportCard";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/app/events/$id")({
  component: EventDetail,
});

function EventDetail() {
  const { id } = Route.useParams();
  const navigate = useNavigate();
  const [workflowResult, setWorkflowResult] = useState<AgentWorkflowResponse | null>(null);
  const [workflowFallback, setWorkflowFallback] = useState(false);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["event", id],
    queryFn: () => api.getEvent(id),
  });

  const runWorkflow = useMutation({
    mutationFn: () => api.runAgentWorkflow(id),
    onSuccess: (result) => {
      setWorkflowResult(result);
      setWorkflowFallback(false);
      toast.success("Workflow completed");
      refetch();
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && [404, 501].includes(error.status)) {
        setWorkflowFallback(true);
        return;
      }
      toast.error(getApiErrorMessage(error, "Failed to run workflow"));
    },
  });

  if (isLoading) return <LoadingState label="Loading event..." />;
  if (error || !data) {
    return (
      <ErrorState
        message={(error as Error)?.message ?? "Event not found"}
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <Link
        to="/app/events"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Back to events
      </Link>

      <header className="glass rounded-xl p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <SeverityBadge value={data.severity} />
              <StatusBadge value={data.status} />
              <span className="text-xs text-muted-foreground">{data.event_type}</span>
            </div>
            <h1 className="mt-3 text-2xl font-semibold tracking-tight">{data.title}</h1>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">{data.description}</p>
            <p className="mt-2 text-xs text-muted-foreground">Source: {data.source}</p>
            <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
              {data.created_at && (
                <span>Created: {new Date(data.created_at).toLocaleString()}</span>
              )}
              {data.updated_at && (
                <span>Updated: {new Date(data.updated_at).toLocaleString()}</span>
              )}
            </div>
          </div>
          <Button
            onClick={() => runWorkflow.mutate()}
            disabled={runWorkflow.isPending}
            className="gap-2"
          >
            <Play className="h-4 w-4" /> {runWorkflow.isPending ? "Running..." : "Run AI Workflow"}
          </Button>
        </div>
      </header>

      <WorkflowTimeline active={workflowResult ? 6 : 0} />

      {workflowResult ? (
        <div className="grid gap-4 lg:grid-cols-3">
          <AnalysisCard icon={Eye} title="Observer" body={workflowResult.observation.summary} />
          <AnalysisCard
            icon={Search}
            title="Investigation"
            body={`${workflowResult.investigation.root_cause} ${workflowResult.investigation.impact}`}
          />
          <AnalysisCard
            icon={TrendingUp}
            title="Prediction"
            body={`Revenue risk $${workflowResult.prediction.revenue_risk.toLocaleString()} with ${(workflowResult.prediction.delay_probability * 100).toFixed(0)}% delay probability.`}
          />
          <AnalysisCard
            icon={Compass}
            title="Strategy"
            body={`${workflowResult.strategies.length} mitigation options generated. Top option: ${workflowResult.strategies[0]?.title ?? "Review required"}.`}
          />
          <AnalysisCard
            icon={Cpu}
            title="Decision"
            body={workflowResult.decision.decision_reason}
          />
          <AnalysisCard
            icon={FileText}
            title="Report"
            body={workflowResult.report.executive_summary}
          />
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          <AnalysisCard
            icon={Eye}
            title="Observer"
            body="Run the AI workflow to generate observation output for this event."
          />
          <AnalysisCard
            icon={Search}
            title="Investigation"
            body="Investigation findings will appear after the backend workflow completes."
          />
          <AnalysisCard
            icon={TrendingUp}
            title="Prediction"
            body="Revenue, delay, churn and severity predictions will appear here."
          />
          <AnalysisCard
            icon={Compass}
            title="Strategy"
            body="Generated mitigation strategies will appear after workflow execution."
          />
          <AnalysisCard
            icon={Cpu}
            title="Decision"
            body="The recommended action and approval requirement will appear here."
          />
          <AnalysisCard
            icon={FileText}
            title="Report"
            body="The executive and technical summaries will appear here."
          />
        </div>
      )}

      {data.metadata && Object.keys(data.metadata).length > 0 && (
        <div className="glass rounded-xl p-5">
          <h3 className="mb-3 font-semibold">Metadata</h3>
          <pre className="overflow-x-auto rounded-lg border border-border bg-background/40 p-3 text-xs">
            {JSON.stringify(data.metadata, null, 2)}
          </pre>
        </div>
      )}

      <div className="glass rounded-xl p-5">
        <h3 className="mb-3 font-semibold">Timeline</h3>
        {data.timeline && data.timeline.length > 0 ? (
          <ol className="space-y-3">
            {data.timeline.map((item) => (
              <li key={item.id} className="rounded-lg border border-border bg-background/40 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-medium">{item.activity_type}</span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(item.created_at).toLocaleString()}
                  </span>
                </div>
                {item.details && Object.keys(item.details).length > 0 && (
                  <pre className="mt-2 overflow-x-auto text-xs text-muted-foreground">
                    {JSON.stringify(item.details, null, 2)}
                  </pre>
                )}
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-sm text-muted-foreground">No activity recorded yet.</p>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-3">
          <h3 className="font-semibold">Recommendations</h3>
          {workflowResult ? (
            workflowResult.strategies.map((strategy) => (
              <RecommendationCard
                key={strategy.title}
                title={strategy.title}
                body={strategy.description}
                confidence={Math.round(strategy.confidence * 100)}
              />
            ))
          ) : (
            <RecommendationCard
              title="Awaiting workflow"
              body="Run the AI workflow to generate event-specific recommendations."
              confidence={0}
            />
          )}
        </div>
        <div className="space-y-3">
          <h3 className="font-semibold">Executive Report</h3>
          <ReportCard
            title={"Incident #" + data.id.slice(0, 6)}
            summary={
              workflowResult?.report.executive_summary ??
              "Auto-generated executive summary will appear here once the agent workflow completes."
            }
            date={workflowResult?.completed_at ?? data.created_at}
          />
        </div>
      </div>

      {workflowFallback && (
        <div className="glass rounded-xl p-6 text-center">
          <Sparkles className="mx-auto h-6 w-6 text-primary" />
          <h3 className="mt-2 font-semibold">AI workflow backend is not available yet</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            AI workflow backend is not available yet. Event management is connected successfully.
          </p>
          <Button
            variant="outline"
            className="mt-3"
            onClick={() => navigate({ to: "/app/agents" })}
          >
            View agents
          </Button>
        </div>
      )}
    </div>
  );
}

function AnalysisCard({
  icon: Icon,
  title,
  body,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  body: string;
}) {
  return (
    <div className="glass rounded-xl p-5">
      <div className="flex items-start gap-3">
        <div className="rounded-lg border border-border bg-background/40 p-2">
          <Icon className="h-4 w-4 text-primary" />
        </div>
        <div>
          <h4 className="font-medium">{title}</h4>
          <p className="mt-1 text-sm text-muted-foreground">{body}</p>
        </div>
      </div>
    </div>
  );
}
