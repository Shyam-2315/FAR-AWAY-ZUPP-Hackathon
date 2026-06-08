import { Link } from "@tanstack/react-router";
import type { Event } from "@/lib/types";
import { SeverityBadge } from "./SeverityBadge";
import { StatusBadge } from "./StatusBadge";
import { Button } from "@/components/ui/button";
import { Pencil, Trash2 } from "lucide-react";

interface EventTableProps {
  events: Event[];
  onEdit?: (e: Event) => void;
  onDelete?: (e: Event) => void;
}

export function EventTable({ events, onEdit, onDelete }: EventTableProps) {
  return (
    <div className="glass overflow-hidden rounded-xl">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-border bg-background/30 text-left text-xs uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-4 py-3">Title</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Source</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr
                key={e.id}
                className="border-b border-border/60 transition hover:bg-background/40"
              >
                <td className="px-4 py-3">
                  <Link
                    to="/app/events/$id"
                    params={{ id: e.id }}
                    className="font-medium hover:text-primary"
                  >
                    {e.title}
                  </Link>
                  <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">
                    {e.description}
                  </p>
                </td>
                <td className="px-4 py-3 text-muted-foreground">{e.event_type}</td>
                <td className="px-4 py-3">
                  <SeverityBadge value={e.severity} />
                </td>
                <td className="px-4 py-3">
                  <StatusBadge value={e.status} />
                </td>
                <td className="px-4 py-3 text-muted-foreground">{e.source ?? "—"}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    {onEdit && (
                      <Button size="icon" variant="ghost" onClick={() => onEdit(e)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                    )}
                    {onDelete && (
                      <Button size="icon" variant="ghost" onClick={() => onDelete(e)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
