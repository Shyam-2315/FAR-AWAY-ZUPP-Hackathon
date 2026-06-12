import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Bell, LogOut, Search, User as UserIcon, AlertTriangle } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function Topbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const { data: alertsData } = useQuery({
    queryKey: ["notifications", "unresolved"],
    queryFn: () =>
      api.events.list({
        status: ["NEW", "IN_PROGRESS"],
        severity: ["HIGH", "CRITICAL"],
        page: 1,
        page_size: 5,
        sort_by: "created_at",
        sort_order: "desc",
      }),
    refetchInterval: 30_000,
  });

  const alerts = alertsData?.items ?? [];
  const alertCount = alertsData?.total ?? 0;

  const initials = user?.name
    ?.split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-border bg-background/60 px-4 backdrop-blur-xl lg:px-6">
      <div className="relative hidden flex-1 max-w-md md:block">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          placeholder="Search events, agents, reports…"
          className="h-9 w-full rounded-lg border border-input bg-background/40 pl-9 pr-3 text-sm outline-none placeholder:text-muted-foreground focus:border-primary"
        />
      </div>
      <div className="ml-auto flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button size="icon" variant="ghost" className="relative">
              <Bell className="h-4 w-4" />
              {alertCount > 0 && (
                <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-semibold leading-none text-destructive-foreground">
                  {alertCount > 9 ? "9+" : alertCount}
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <DropdownMenuLabel>
              Notifications
              {alertCount > 0 && (
                <span className="ml-1 text-xs text-muted-foreground">
                  ({alertCount} unresolved)
                </span>
              )}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            {alerts.length === 0 ? (
              <div className="px-3 py-6 text-center text-sm text-muted-foreground">
                No new notifications.
              </div>
            ) : (
              <div className="max-h-80 overflow-y-auto">
                {alerts.map((event) => (
                  <DropdownMenuItem
                    key={event.id}
                    className="flex flex-col items-start gap-1 whitespace-normal py-2"
                    onClick={() => navigate({ to: "/app/events/$id", params: { id: event.id } })}
                  >
                    <div className="flex w-full items-center gap-2">
                      <AlertTriangle
                        className={`h-3.5 w-3.5 shrink-0 ${
                          event.severity === "CRITICAL" ? "text-destructive" : "text-amber-500"
                        }`}
                      />
                      <span className="truncate text-sm font-medium">{event.title}</span>
                    </div>
                    <div className="flex w-full items-center justify-between text-xs text-muted-foreground">
                      <span>{event.event_type}</span>
                      <span>
                        {event.severity} · {event.status}
                      </span>
                    </div>
                  </DropdownMenuItem>
                ))}
              </div>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2 rounded-lg border border-border bg-background/40 px-2 py-1.5 text-sm hover:bg-background/70">
              <div
                className="flex h-7 w-7 items-center justify-center rounded-md text-xs font-semibold"
                style={{ background: "var(--gradient-primary)", color: "var(--background)" }}
              >
                {initials || <UserIcon className="h-4 w-4" />}
              </div>
              <div className="hidden text-left md:block">
                <div className="text-xs font-medium leading-none">{user?.name ?? "Guest"}</div>
                <div className="text-[10px] text-muted-foreground">{user?.role}</div>
              </div>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="text-sm">{user?.name}</div>
              <div className="text-xs text-muted-foreground">{user?.email}</div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => navigate({ to: "/app/settings" })}>
              <UserIcon className="mr-2 h-4 w-4" /> Settings
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={async () => {
                await logout();
                navigate({ to: "/login" });
              }}
            >
              <LogOut className="mr-2 h-4 w-4" /> Logout
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}