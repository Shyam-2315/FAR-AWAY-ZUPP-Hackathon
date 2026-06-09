import { useEffect, useState, type ReactNode } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Event, Severity, Status } from "@/lib/types";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, getApiErrorMessage } from "@/lib/api";
import { toast } from "sonner";

const severities: Severity[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
const statuses: Status[] = ["NEW", "IN_PROGRESS", "RESOLVED", "FAILED"];

interface FormState {
  title: string;
  description: string;
  event_type: string;
  severity: Severity;
  status: Status;
  source: string;
  tenant_id: string;
  metadata: string;
}

const empty: FormState = {
  title: "Suspicious Login Attempt",
  description: "Multiple failed login attempts detected from unknown IP.",
  event_type: "AUTHENTICATION",
  severity: "HIGH",
  status: "NEW",
  source: "auth-service",
  tenant_id: "demo-tenant",
  metadata: JSON.stringify(
    {
      ip: "192.168.1.50",
      failed_attempts: 8,
      country: "Unknown",
      user_agent: "Chrome on Windows",
    },
    null,
    2,
  ),
};

interface EventModalProps {
  mode: "create" | "edit";
  event?: Event;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  trigger?: ReactNode;
}

export function EventModal({ mode, event, open, onOpenChange, trigger }: EventModalProps) {
  const qc = useQueryClient();
  const [internalOpen, setInternalOpen] = useState(false);
  const isOpen = open ?? internalOpen;
  const setOpen = onOpenChange ?? setInternalOpen;

  const [form, setForm] = useState<FormState>(() =>
    event
      ? {
          title: event.title,
          description: event.description ?? "",
          event_type: event.event_type,
          severity: event.severity,
          status: event.status,
          source: event.source ?? "",
          tenant_id: event.tenant_id ?? "",
          metadata: event.metadata ? JSON.stringify(event.metadata, null, 2) : "",
        }
      : empty,
  );

  useEffect(() => {
    if (mode !== "edit" || !event) return;
    setForm({
      title: event.title,
      description: event.description ?? "",
      event_type: event.event_type,
      severity: event.severity,
      status: event.status,
      source: event.source ?? "",
      tenant_id: event.tenant_id ?? "",
      metadata: event.metadata ? JSON.stringify(event.metadata, null, 2) : "",
    });
  }, [event, mode]);

  const mutation = useMutation({
    mutationFn: async () => {
      let metadata: Record<string, unknown> = {};
      if (form.metadata.trim()) {
        try {
          const parsed = JSON.parse(form.metadata);
          if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
            throw new Error("Metadata must be a JSON object");
          }
          metadata = parsed as Record<string, unknown>;
        } catch {
          throw new Error("Metadata must be a valid JSON object");
        }
      }
      const payload = {
        title: form.title.trim(),
        description: form.description.trim() || null,
        event_type: form.event_type.trim(),
        severity: form.severity,
        status: form.status,
        source: form.source.trim() || "manual",
        tenant_id: form.tenant_id.trim() || null,
        metadata,
      };
      if (mode === "create") return api.createEvent(payload);
      return api.updateEvent(event!.id, payload);
    },
    onSuccess: () => {
      toast.success(mode === "create" ? "Event created" : "Event updated");
      qc.invalidateQueries({ queryKey: ["events"] });
      if (event) qc.invalidateQueries({ queryKey: ["event", event.id] });
      setOpen(false);
      if (mode === "create") setForm(empty);
    },
    onError: (error: unknown) => toast.error(getApiErrorMessage(error, "Failed")),
  });

  return (
    <Dialog open={isOpen} onOpenChange={setOpen}>
      {trigger && <DialogTrigger asChild>{trigger}</DialogTrigger>}
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{mode === "create" ? "Create Event" : "Edit Event"}</DialogTitle>
          <DialogDescription>
            Operational signal that Athena will observe, investigate and act on.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-3">
          <div>
            <Label>Title</Label>
            <Input
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="Shipment Delay on Route A"
            />
          </div>
          <div>
            <Label>Description</Label>
            <Textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={3}
              placeholder="Heavy rainfall has delayed multiple shipments…"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Event type</Label>
              <Input
                value={form.event_type}
                onChange={(e) => setForm({ ...form, event_type: e.target.value })}
              />
            </div>
            <div>
              <Label>Source</Label>
              <Input
                value={form.source}
                onChange={(e) => setForm({ ...form, source: e.target.value })}
              />
            </div>
            <div>
              <Label>Tenant ID</Label>
              <Input
                value={form.tenant_id}
                onChange={(e) => setForm({ ...form, tenant_id: e.target.value })}
              />
            </div>
            <div>
              <Label>Severity</Label>
              <Select
                value={form.severity}
                onValueChange={(v) => setForm({ ...form, severity: v as Severity })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {severities.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Status</Label>
              <Select
                value={form.status}
                onValueChange={(v) => setForm({ ...form, status: v as Status })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {statuses.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div>
            <Label>Metadata (JSON)</Label>
            <Textarea
              value={form.metadata}
              onChange={(e) => setForm({ ...form, metadata: e.target.value })}
              rows={4}
              placeholder='{"region": "Ahmedabad", "estimated_loss": 125000}'
              className="font-mono text-xs"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={
              mutation.isPending ||
              !form.title.trim() ||
              !form.event_type.trim() ||
              !form.source.trim()
            }
          >
            {mutation.isPending ? "Saving…" : mode === "create" ? "Create event" : "Save changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
