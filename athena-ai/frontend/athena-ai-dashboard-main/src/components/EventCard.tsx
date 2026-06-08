import { Link } from "@tanstack/react-router";
import type { Event } from "@/lib/types";
import { SeverityBadge } from "./SeverityBadge";
import { StatusBadge } from "./StatusBadge";
import { ArrowRight } from "lucide-react";

export function EventCard({ event }: { event: Event }) {
  return (
    <Link
      to="/app/events/$id"
      params={{ id: event.id }}
      className="glass group block rounded-xl p-5 transition hover:border-primary/40"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold">{event.title}</h3>
          <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{event.description}</p>
        </div>
        <ArrowRight className="h-4 w-4 text-muted-foreground transition group-hover:translate-x-1 group-hover:text-primary" />
      </div>
      <div className="mt-4 flex items-center gap-2">
        <SeverityBadge value={event.severity} />
        <StatusBadge value={event.status} />
        <span className="ml-auto text-xs text-muted-foreground">{event.event_type}</span>
      </div>
    </Link>
  );
}
