import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api, API_BASE_URL, tokenStore, getApiErrorMessage } from "@/lib/api";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { LoadingState } from "@/components/LoadingState";
import { Download, FileText, CheckCircle2, AlertCircle } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/app/reports")({
  component: ReportsPage,
});

function ReportsPage() {
  // ------------------------------------------------------------------ //
  // FIX 4: State for the selected event and download progress.
  // ------------------------------------------------------------------ //
  const [selectedEventId, setSelectedEventId] = useState<string>("");
  const [isDownloading, setIsDownloading] = useState(false);

  // Load all RESOLVED events so the user only sees events that have a
  // completed agent workflow and therefore an actual report to export.
  const { data: eventsData, isLoading: eventsLoading } = useQuery({
    queryKey: ["events", { status: "RESOLVED", page_size: 100 }],
    queryFn: () =>
      api.listEvents({ status: "RESOLVED", page: 1, page_size: 100, sort_by: "created_at", sort_order: "desc" }),
  });

  const resolvedEvents = eventsData?.items ?? [];

  // The currently selected event object (for displaying metadata).
  const selectedEvent = resolvedEvents.find((e) => e.id === selectedEventId) ?? null;

  // ------------------------------------------------------------------ //
  // FIX 4: Export PDF handler
  //
  // Uses a direct fetch() instead of the shared api.request() helper
  // because we need to receive a binary Blob response, not JSON.
  // The JWT is read from tokenStore (same localStorage key the rest of
  // the app uses) and attached as a Bearer Authorization header so the
  // FastAPI RBAC dependency passes.
  //
  // The browser "download" trick (anchor.click()) works cross-browser and
  // doesn't require any popup / new tab — the file arrives as an
  // attachment stream from the StreamingResponse FastAPI sends back.
  // ------------------------------------------------------------------ //
  const handleExportPdf = async () => {
    if (!selectedEventId) {
      toast.error("Please select a resolved event first.");
      return;
    }

    setIsDownloading(true);
    try {
      const token = tokenStore.getAccess();
      const url = `${API_BASE_URL}/api/reports/${selectedEventId}/pdf`;

      const res = await fetch(url, {
        method: "GET",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!res.ok) {
        // Try to parse an error body; fall back to a generic message.
        let detail = `Server responded with ${res.status}`;
        try {
          const errData = await res.json();
          if (errData?.detail?.message) detail = errData.detail.message;
          else if (typeof errData?.detail === "string") detail = errData.detail;
        } catch {
          // ignore JSON parse failure
        }
        throw new Error(detail);
      }

      // Convert the streamed PDF into a local object URL and trigger a
      // browser download — no new tab, no popup.
      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");

      // Use the filename from Content-Disposition if the server sent one,
      // otherwise fall back to a sensible default.
      const disposition = res.headers.get("Content-Disposition") ?? "";
      const match = disposition.match(/filename="?([^"]+)"?/);
      anchor.download = match?.[1] ?? `athena-report-${selectedEventId}.pdf`;
      anchor.href = objectUrl;
      anchor.click();

      // Clean up the object URL after a short delay.
      setTimeout(() => URL.revokeObjectURL(objectUrl), 5000);

      toast.success("PDF downloaded successfully.");
    } catch (err: unknown) {
      toast.error(getApiErrorMessage(err, "PDF export failed. Check backend logs."));
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* ---------------------------------------------------------------- */}
      {/* Header                                                            */}
      {/* ---------------------------------------------------------------- */}
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Executive Reports</h1>
          <p className="text-sm text-muted-foreground">
            Download structured PDF reports for any completed AI workflow.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* FIX 4: Export PDF — enabled only when an event is selected */}
          <Button
            className="gap-2"
            disabled={!selectedEventId || isDownloading}
            onClick={handleExportPdf}
          >
            <Download className={`h-4 w-4 ${isDownloading ? "animate-bounce" : ""}`} />
            {isDownloading ? "Generating PDF…" : "Export PDF"}
          </Button>
        </div>
      </header>

      {/* ---------------------------------------------------------------- */}
      {/* FIX 4: Event selector panel                                       */}
      {/* ---------------------------------------------------------------- */}
      <section className="glass rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
            Select a Resolved Event
          </h2>
        </div>

        {eventsLoading ? (
          <LoadingState label="Loading resolved events…" />
        ) : resolvedEvents.length === 0 ? (
          <div className="flex items-center gap-2 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>
              No resolved events found. Run an AI Core workflow from the Events page to generate a
              report, then return here to export it.
            </span>
          </div>
        ) : (
          <div className="flex flex-wrap items-center gap-3">
            <Select value={selectedEventId} onValueChange={setSelectedEventId}>
              <SelectTrigger className="w-full max-w-md">
                <SelectValue placeholder="Choose a resolved event…" />
              </SelectTrigger>
              <SelectContent>
                {resolvedEvents.map((event) => (
                  <SelectItem key={event.id} value={event.id}>
                    <span className="flex items-center gap-2">
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                      {event.title}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {selectedEventId && (
              <Button
                className="gap-2"
                disabled={isDownloading}
                onClick={handleExportPdf}
              >
                <Download className={`h-4 w-4 ${isDownloading ? "animate-bounce" : ""}`} />
                {isDownloading ? "Generating…" : "Export PDF"}
              </Button>
            )}
          </div>
        )}
      </section>

      {/* ---------------------------------------------------------------- */}
      {/* FIX 4: Selected event preview card                               */}
      {/* ---------------------------------------------------------------- */}
      {selectedEvent && (
        <section className="glass rounded-2xl p-6 space-y-3">
          <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
            Report Preview
          </h2>
          <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm sm:grid-cols-3">
            <div>
              <p className="text-xs text-muted-foreground">Title</p>
              <p className="font-medium">{selectedEvent.title}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Type</p>
              <p className="font-medium">{selectedEvent.event_type}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Severity</p>
              <p className="font-medium">{selectedEvent.severity}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Status</p>
              <p className="font-medium text-emerald-500">{selectedEvent.status}</p>
            </div>
            {selectedEvent.tenant_id && (
              <div>
                <p className="text-xs text-muted-foreground">Tenant</p>
                <p className="font-medium">{selectedEvent.tenant_id}</p>
              </div>
            )}
            <div>
              <p className="text-xs text-muted-foreground">Event ID</p>
              <p className="font-mono text-xs text-muted-foreground">{selectedEvent.id}</p>
            </div>
          </div>

          <div className="pt-2">
            <Button
              size="lg"
              className="gap-2 w-full sm:w-auto"
              disabled={isDownloading}
              onClick={handleExportPdf}
            >
              <Download className={`h-4 w-4 ${isDownloading ? "animate-bounce" : ""}`} />
              {isDownloading
                ? "Building PDF — please wait…"
                : `Download PDF Report`}
            </Button>
          </div>
        </section>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Info section explaining the workflow                             */}
      {/* ---------------------------------------------------------------- */}
      <section className="glass rounded-2xl p-6">
        <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          How Reports Work
        </h2>
        <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
          PDF reports are generated on demand from the AI agent outputs stored in PostgreSQL.
          Each report includes the executive summary, technical root-cause analysis, financial
          impact estimate, confidence score, and the full agent pipeline trace
          (Observer → Investigator → Predictor → Strategy → Decision Engine).
          Only events with status <span className="text-emerald-500 font-medium">RESOLVED</span> have
          a completed workflow and are available for export.
        </p>
      </section>
    </div>
  );
}