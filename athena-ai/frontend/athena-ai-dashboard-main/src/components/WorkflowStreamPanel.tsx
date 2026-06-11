/**
 * WorkflowStreamPanel
 *
 * Real-time agent workflow progress panel driven by Server-Sent Events.
 * Uses a ref-based completion guard to prevent EventSource auto-reconnect.
 */

import { useEffect, useRef, useState } from "react";
import { API_BASE_URL, tokenStore } from "@/lib/api";
import type { AgentWorkflowResponse } from "@/lib/types";
import {
  CheckCircle2,
  Circle,
  Loader2,
  XCircle,
  ChevronDown,
  ChevronUp,
  X,
  Brain,
  AlertTriangle,
} from "lucide-react";

type NodeStatus = "waiting" | "running" | "done" | "error";

interface AgentNode {
  key: string;
  label: string;
  sublabel: string;
  status: NodeStatus;
  data: unknown;
  completedAt: string | null;
}

interface StreamEvent {
  node?: string;
  label?: string;
  progress?: number;
  total?: number;
  data?: unknown;
  errors?: string[];
  message?: string;
  event_id?: string;
  event_title?: string;
  total_nodes?: number;
  observation?: unknown;
  investigation?: unknown;
  prediction?: unknown;
  strategies?: unknown;
  decision?: unknown;
  report?: unknown;
  confidence_score?: number;
  started_at?: string;
  completed_at?: string;
  event_status?: string;
}

const PIPELINE_NODES: Omit<AgentNode, "status" | "data" | "completedAt">[] = [
  { key: "observer",      label: "Observer",        sublabel: "Analysing the incoming signal" },
  { key: "investigation", label: "Investigator",    sublabel: "Finding the root cause" },
  { key: "prediction",    label: "Predictor",       sublabel: "Calculating financial exposure" },
  { key: "strategy",      label: "Strategy Agent",  sublabel: "Evaluating response options" },
  { key: "decision",      label: "Decision Engine", sublabel: "Choosing the optimal action" },
  { key: "reporting",     label: "Reporting Agent", sublabel: "Writing executive summary" },
];

interface WorkflowStreamPanelProps {
  eventId: string;
  eventTitle: string;
  onComplete?: (result: AgentWorkflowResponse) => void;
  onClose?: () => void;
}

export function WorkflowStreamPanel({
  eventId,
  eventTitle,
  onComplete,
  onClose,
}: WorkflowStreamPanelProps) {
  const [nodes, setNodes] = useState<AgentNode[]>(
    PIPELINE_NODES.map((n) => ({ ...n, status: "waiting", data: null, completedAt: null })),
  );
  const [globalStatus, setGlobalStatus] = useState<
    "idle" | "connecting" | "running" | "done" | "error"
  >("connecting");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [expandedNode, setExpandedNode] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);

  const esRef = useRef<EventSource | null>(null);
  const startTimeRef = useRef<number>(Date.now());
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // KEY FIX: useRef instead of let — persists across re-renders and is
  // readable instantly from all event listener closures with no timing gap.
  const isCompleteRef = useRef(false);

  useEffect(() => {
    const token = tokenStore.getAccess();
    if (!token) {
      setGlobalStatus("error");
      setErrorMessage("No access token found. Please log in again.");
      return;
    }

    isCompleteRef.current = false;

    const url = `${API_BASE_URL}/api/agents/stream/${eventId}?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);
    esRef.current = es;

    // Always close on network error — never allow EventSource to auto-reconnect.
    es.onerror = () => {
      es.close();
      if (!isCompleteRef.current) {
        isCompleteRef.current = true;
        setGlobalStatus("error");
        setErrorMessage(
          "Connection lost. The workflow may have completed — check event status.",
        );
        if (timerRef.current) clearInterval(timerRef.current);
        setNodes((prev) =>
          prev.map((n) => (n.status === "running" ? { ...n, status: "error" } : n)),
        );
      }
    };

    startTimeRef.current = Date.now();
    timerRef.current = setInterval(() => {
      setElapsedMs(Date.now() - startTimeRef.current);
    }, 500);

    es.addEventListener("started", () => {
      setGlobalStatus("running");
      setNodes((prev) =>
        prev.map((n, i) => (i === 0 ? { ...n, status: "running" } : n)),
      );
    });

    es.addEventListener("node_complete", (e: MessageEvent) => {
      const payload: StreamEvent = JSON.parse(e.data);
      const { node, progress = 0, total = 6, data } = payload;
      setNodes((prev) =>
        prev.map((n) => {
          if (n.key === node) {
            return { ...n, status: "done", data, completedAt: new Date().toISOString() };
          }
          const currentIdx = PIPELINE_NODES.findIndex((p) => p.key === node);
          const nextNode = PIPELINE_NODES[currentIdx + 1];
          if (nextNode && n.key === nextNode.key && progress < total) {
            return { ...n, status: "running" };
          }
          return n;
        }),
      );
    });

    es.addEventListener("done", (e: MessageEvent) => {
      if (isCompleteRef.current) return;
      isCompleteRef.current = true;
      const payload: StreamEvent = JSON.parse(e.data);
      setGlobalStatus("done");
      setConfidence(payload.confidence_score ?? null);
      if (timerRef.current) clearInterval(timerRef.current);
      setNodes((prev) => prev.map((n) => ({ ...n, status: "done" })));
      if (onComplete) {
        onComplete(payload as unknown as AgentWorkflowResponse);
      }
      es.close();
    });

    es.addEventListener("error", (e: MessageEvent | Event) => {
      if (isCompleteRef.current) return;
      isCompleteRef.current = true;
      let msg = "Workflow failed. Check backend logs.";
      if (e instanceof MessageEvent) {
        try {
          const parsed: StreamEvent = JSON.parse(e.data);
          msg = parsed.message ?? msg;
        } catch {
          // ignore
        }
      }
      setGlobalStatus("error");
      setErrorMessage(msg);
      if (timerRef.current) clearInterval(timerRef.current);
      setNodes((prev) =>
        prev.map((n) => (n.status === "running" ? { ...n, status: "error" } : n)),
      );
      es.close();
    });

    return () => {
      isCompleteRef.current = true;
      es.close();
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [eventId, onComplete]);

  const completedCount = nodes.filter((n) => n.status === "done").length;
  const progressPct = Math.round((completedCount / PIPELINE_NODES.length) * 100);
  const elapsedSec = (elapsedMs / 1000).toFixed(1);

  function formatData(data: unknown): string {
    if (!data) return "No output";
    return JSON.stringify(data, null, 2);
  }

  function getNodeLabelClass(status: NodeStatus): string {
    if (status === "waiting") return "text-muted-foreground";
    if (status === "running") return "text-violet-300";
    if (status === "done") return "text-foreground";
    return "text-red-400";
  }

  function getProgressBarClass(): string {
    if (globalStatus === "error") return "bg-red-500";
    if (globalStatus === "done") return "bg-emerald-500";
    return "bg-violet-500";
  }

  return (
    <div className="glass rounded-2xl overflow-hidden border border-white/10">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <Brain className="h-5 w-5 text-violet-400" />
          <div>
            <p className="text-sm font-semibold">AI Core Running</p>
            <p className="text-xs text-muted-foreground truncate max-w-[280px]">
              {eventTitle}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {globalStatus === "running" && (
            <span className="text-xs text-muted-foreground tabular-nums">{elapsedSec}s</span>
          )}
          {globalStatus === "done" && confidence !== null && (
            <span className="text-xs font-medium text-emerald-400">
              {(confidence * 100).toFixed(0)}% confidence
            </span>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="rounded p-1 hover:bg-white/10 transition-colors"
              aria-label="Close panel"
            >
              <X className="h-4 w-4 text-muted-foreground" />
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-white/5">
        <div
          className={`h-full transition-all duration-700 ${getProgressBarClass()}`}
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Error banner */}
      {globalStatus === "error" && errorMessage && (
        <div className="mx-4 mt-4 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Agent pipeline nodes */}
      <div className="divide-y divide-white/5 px-2 py-2">
        {nodes.map((node, idx) => {
          const isExpanded = expandedNode === node.key;
          return (
            <div key={node.key} className="rounded-lg">
              <button
                className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg text-left transition-colors ${
                  node.status === "done"
                    ? "hover:bg-white/5 cursor-pointer"
                    : "cursor-default"
                }`}
                onClick={() => {
                  if (node.status === "done") {
                    setExpandedNode(isExpanded ? null : node.key);
                  }
                }}
                disabled={node.status !== "done"}
              >
                {/* Status icon */}
                <div className="shrink-0">
                  {node.status === "waiting" && (
                    <Circle className="h-5 w-5 text-white/20" />
                  )}
                  {node.status === "running" && (
                    <Loader2 className="h-5 w-5 text-violet-400 animate-spin" />
                  )}
                  {node.status === "done" && (
                    <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                  )}
                  {node.status === "error" && (
                    <XCircle className="h-5 w-5 text-red-400" />
                  )}
                </div>

                {/* Label */}
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium ${getNodeLabelClass(node.status)}`}>
                    {idx + 1}. {node.label}
                  </p>
                  <p className="text-xs text-muted-foreground">{node.sublabel}</p>
                </div>

                {/* Expand toggle */}
                {node.status === "done" && node.data && (
                  <div className="shrink-0 text-muted-foreground">
                    {isExpanded ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </div>
                )}
              </button>

              {/* Expanded output drawer */}
              {isExpanded && node.data && (
                <div className="mx-3 mb-3 rounded-lg bg-black/30 border border-white/10 p-3">
                  <pre className="text-xs text-muted-foreground overflow-auto max-h-48 whitespace-pre-wrap">
                    {formatData(node.data)}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      {globalStatus === "done" && (
        <div className="px-5 py-4 border-t border-white/10 flex items-center justify-between">
          <p className="text-sm text-emerald-400 font-medium">
            ✓ Workflow complete — event resolved
          </p>
          <p className="text-xs text-muted-foreground">{elapsedSec}s total</p>
        </div>
      )}
      {globalStatus === "connecting" && (
        <div className="px-5 py-4 flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Connecting to AI Core…
        </div>
      )}
    </div>
  );
}