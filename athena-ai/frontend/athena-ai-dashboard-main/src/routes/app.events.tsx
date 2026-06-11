import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getApiErrorMessage } from "@/lib/api";
import { useEffect, useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EventTable } from "@/components/EventTable";
import { EventModal } from "@/components/EventModal";
import { DeleteConfirmDialog } from "@/components/DeleteConfirmDialog";
import { LoadingState } from "@/components/LoadingState";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { WorkflowStreamPanel } from "@/components/WorkflowStreamPanel";
import type { AgentWorkflowResponse, Event, Severity, Status } from "@/lib/types";
import { Plus, Search, ChevronLeft, ChevronRight, Brain } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/app/events")({
  component: EventsPage,
});

function EventsPage() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [q, setQ] = useState("");
  const [severity, setSeverity] = useState<string>("all");
  const [status, setStatus] = useState<string>("all");
  const [type, setType] = useState<string>("");
  const [tenantId, setTenantId] = useState<string>("");
  const [sort, setSort] = useState("recent");
  const [createOpen, setCreateOpen] = useState(false);
  const [editEvent, setEditEvent] = useState<Event | null>(null);
  const [deleteEvent, setDeleteEvent] = useState<Event | null>(null);

  // ── SSE streaming state ─────────────────────────────────────────────── //
  // activeStream holds the event being streamed right now.
  // When non-null, the WorkflowStreamPanel is rendered below the table.
  const [activeStream, setActiveStream] = useState<{
    eventId: string;
    eventTitle: string;
  } | null>(null);

  const sortParams = useMemo(() => {
    if (sort === "severity") return { sort_by: "severity" as const, sort_order: "desc" as const };
    if (sort === "updated") return { sort_by: "updated_at" as const, sort_order: "desc" as const };
    if (sort === "status") return { sort_by: "status" as const, sort_order: "asc" as const };
    if (sort === "event_type")
      return { sort_by: "event_type" as const, sort_order: "asc" as const };
    if (sort === "title") return { sort_by: "title" as const, sort_order: "asc" as const };
    return { sort_by: "created_at" as const, sort_order: "desc" as const };
  }, [sort]);

  useEffect(() => {
    setPage(1);
  }, [q, severity, status, type, tenantId, sort]);

  const queryParams = {
    page,
    page_size: pageSize,
    search: q || undefined,
    severity: severity === "all" ? undefined : (severity as Severity),
    status: status === "all" ? undefined : (status as Status),
    event_type: type || undefined,
    tenant_id: tenantId || undefined,
    ...sortParams,
  };

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["events", queryParams],
    queryFn: () => api.listEvents(queryParams),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 1;

  const delMut = useMutation({
    mutationFn: (id: string) => api.deleteEvent(id),
    onSuccess: () => {
      toast.success("Event deleted");
      qc.invalidateQueries({ queryKey: ["events"] });
      setDeleteEvent(null);
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, "Failed to delete")),
  });

  // ── Launch SSE stream for a specific event ──────────────────────────── //
  const handleRunWorkflow = (event: Event) => {
    if (activeStream) {
      toast.warning("A workflow is already running. Wait for it to finish.");
      return;
    }
    setActiveStream({ eventId: event.id, eventTitle: event.title });
  };

  // ── Called by WorkflowStreamPanel when the "done" SSE event arrives ─── //
  const handleStreamComplete = (result: AgentWorkflowResponse) => {
    const savings = result?.report?.estimated_savings;
    const savingsStr =
      savings != null
        ? `Estimated savings: $${Number(savings).toLocaleString()}`
        : "Workflow completed.";

    toast.success(`AI Core finished — ${savingsStr}`);

    // Clear the active stream FIRST before invalidating queries.
    // If we invalidate first, React re-renders with activeStream still set,
    // which remounts WorkflowStreamPanel and starts a new SSE connection.
    setActiveStream(null);

    // Then refresh the events list so status badges flip NEW → RESOLVED
    qc.invalidateQueries({ queryKey: ["events"] });
  };

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Events</h1>
          <p className="text-sm text-muted-foreground">
            All operational signals captured by Athena.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} className="gap-2">
          <Plus className="h-4 w-4" /> Create Event
        </Button>
      </header>

      {/* ── Filter bar ──────────────────────────────────────────────────── */}
      <div className="glass rounded-xl p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-[220px] flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search title or description…"
              className="pl-9"
            />
          </div>
          <Select value={severity} onValueChange={setSeverity}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Severity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All severity</SelectItem>
              {(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as Severity[]).map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All status</SelectItem>
              {(["NEW", "IN_PROGRESS", "RESOLVED", "FAILED"] as Status[]).map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            value={type}
            onChange={(e) => setType(e.target.value)}
            placeholder="event_type…"
            className="w-[180px]"
          />
          <Input
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
            placeholder="tenant_id..."
            className="w-[180px]"
          />
          <Select value={sort} onValueChange={setSort}>
            <SelectTrigger className="w-[160px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="recent">Sort: Recent</SelectItem>
              <SelectItem value="updated">Sort: Updated</SelectItem>
              <SelectItem value="severity">Sort: Severity</SelectItem>
              <SelectItem value="status">Sort: Status</SelectItem>
              <SelectItem value="event_type">Sort: Type</SelectItem>
              <SelectItem value="title">Sort: Title</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* ── Table / states ──────────────────────────────────────────────── */}
      {isLoading ? (
        <LoadingState label="Loading events…" />
      ) : error ? (
        <ErrorState message={(error as Error).message} onRetry={() => refetch()} />
      ) : (data?.items ?? []).length === 0 ? (
        <EmptyState
          title="No events found"
          description="Adjust filters or create a new event."
          actionLabel="Create Event"
          onAction={() => setCreateOpen(true)}
        />
      ) : (
        <>
          <EventTable
            events={data?.items ?? []}
            onEdit={(e) => setEditEvent(e)}
            onDelete={(e) => setDeleteEvent(e)}
          />

          {/* ── Run AI Core action strip — one button per event ──────── */}
          <div className="glass rounded-xl p-4">
            <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Run AI Core
            </p>
            <div className="flex flex-wrap gap-2">
              {(data?.items ?? []).map((event) => {
                const isThisRunning = activeStream?.eventId === event.id;
                const isOtherRunning = activeStream !== null && activeStream.eventId !== event.id;
                return (
                  <Button
                    key={event.id}
                    size="sm"
                    variant={isThisRunning ? "default" : "outline"}
                    className="gap-2"
                    disabled={isOtherRunning}
                    onClick={() => handleRunWorkflow(event)}
                    title={`Run AI Core on: ${event.title}`}
                  >
                    <Brain
                      className={`h-3.5 w-3.5 ${isThisRunning ? "animate-pulse text-violet-300" : ""}`}
                    />
                    {isThisRunning ? "Running…" : "Run AI Core"}
                    <span className="max-w-[140px] truncate text-xs opacity-60">
                      {event.title}
                    </span>
                  </Button>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* ── Live SSE stream panel ─────────────────────────────────────── */}
      {activeStream && (
        <WorkflowStreamPanel
          eventId={activeStream.eventId}
          eventTitle={activeStream.eventTitle}
          onComplete={handleStreamComplete}
          onClose={() => setActiveStream(null)}
        />
      )}

      {/* ── Pagination ───────────────────────────────────────────────── */}
      {data && data.total > pageSize && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {page} of {totalPages} — {data.total} total
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              <ChevronLeft className="h-4 w-4" /> Prev
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      <EventModal mode="create" open={createOpen} onOpenChange={setCreateOpen} />
      {editEvent && (
        <EventModal
          mode="edit"
          event={editEvent}
          open={!!editEvent}
          onOpenChange={(o) => !o && setEditEvent(null)}
        />
      )}
      <DeleteConfirmDialog
        open={!!deleteEvent}
        onOpenChange={(o) => !o && setDeleteEvent(null)}
        onConfirm={() => deleteEvent && delMut.mutate(deleteEvent.id)}
        title="Delete this event?"
        description={deleteEvent ? `"${deleteEvent.title}" will be permanently removed.` : ""}
        loading={delMut.isPending}
      />
    </div>
  );
}