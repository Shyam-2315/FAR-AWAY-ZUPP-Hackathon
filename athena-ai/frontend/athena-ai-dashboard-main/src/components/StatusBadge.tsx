import { cn } from "@/lib/utils";
import type { Status } from "@/lib/types";

const styles: Record<Status, string> = {
  NEW: "bg-sky-500/15 text-sky-300 border-sky-500/30",
  PROCESSING: "bg-violet-500/15 text-violet-300 border-violet-500/30",
  RESOLVED: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  FAILED: "bg-red-500/15 text-red-300 border-red-500/30",
};

export function StatusBadge({ value, className }: { value: Status; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium uppercase tracking-wide",
        styles[value],
        className,
      )}
    >
      {value}
    </span>
  );
}
