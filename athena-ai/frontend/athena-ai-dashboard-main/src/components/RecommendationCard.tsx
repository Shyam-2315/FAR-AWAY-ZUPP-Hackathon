import { Sparkles } from "lucide-react";

interface RecommendationCardProps {
  title: string;
  body: string;
  confidence?: number;
}

export function RecommendationCard({ title, body, confidence }: RecommendationCardProps) {
  return (
    <div className="glass rounded-xl p-5">
      <div className="flex items-start gap-3">
        <div className="rounded-lg border border-border bg-background/40 p-2">
          <Sparkles className="h-4 w-4 text-primary" />
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between gap-2">
            <h4 className="font-medium">{title}</h4>
            {confidence !== undefined && (
              <span className="rounded-md bg-primary/15 px-2 py-0.5 text-[10px] uppercase tracking-wider text-primary">
                {confidence}% conf
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">{body}</p>
        </div>
      </div>
    </div>
  );
}
