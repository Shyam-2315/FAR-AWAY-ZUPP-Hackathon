import { FileText, Download } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ReportCardProps {
  title: string;
  summary: string;
  date?: string;
}

export function ReportCard({ title, summary, date }: ReportCardProps) {
  return (
    <div className="glass rounded-xl p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="rounded-lg border border-border bg-background/40 p-2">
            <FileText className="h-4 w-4 text-primary" />
          </div>
          <div>
            <h3 className="font-semibold">{title}</h3>
            {date && <p className="text-xs text-muted-foreground">{date}</p>}
          </div>
        </div>
        <Button size="sm" variant="outline" className="gap-1.5">
          <Download className="h-3.5 w-3.5" /> PDF
        </Button>
      </div>
      <p className="mt-3 text-sm text-muted-foreground">{summary}</p>
    </div>
  );
}
