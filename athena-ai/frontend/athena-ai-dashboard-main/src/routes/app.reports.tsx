import { createFileRoute } from "@tanstack/react-router";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { Download, FileText } from "lucide-react";

export const Route = createFileRoute("/app/reports")({
  component: ReportsPage,
});

function ReportsPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Executive Reports</h1>
          <p className="text-sm text-muted-foreground">
            Report history will connect here when persisted reports are added to the backend.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" className="gap-2" disabled>
            <FileText className="h-4 w-4" /> Reports API pending
          </Button>
          <Button className="gap-2" disabled>
            <Download className="h-4 w-4" /> Export PDF
          </Button>
        </div>
      </header>

      <section className="glass rounded-2xl p-6">
        <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Roadmap
        </h2>
        <p className="mt-2 text-lg">
          Workflow reports are returned immediately from event detail runs today. Persisted report
          history, filtering, and exports are planned for the next backend phase.
        </p>
      </section>

      <EmptyState
        title="No persisted reports yet"
        description="Run an AI workflow from an event detail page to see the live report response."
      />
    </div>
  );
}
