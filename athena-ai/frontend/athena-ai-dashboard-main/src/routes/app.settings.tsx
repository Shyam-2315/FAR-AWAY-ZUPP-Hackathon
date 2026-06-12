import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useAuth } from "@/lib/auth-context";
import { API_BASE_URL, tokenStore } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { LogOut, Moon, Sun, Copy } from "lucide-react";
import { toast } from "sonner";
import { useEffect, useState } from "react";

export const Route = createFileRoute("/app/settings")({
  component: SettingsPage,
});

function SettingsPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains("dark"));
  }, []);

  const toggleTheme = () => {
    const next = !isDark;
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("athena-theme", next ? "dark" : "light");
    setIsDark(next);
  };

  const hasToken = !!tokenStore.getAccess();

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Manage your account and app preferences.</p>
      </header>

      <section className="glass rounded-xl p-6">
        <h2 className="font-semibold">Profile</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <Info label="Name" value={user?.name ?? "—"} />
          <Info label="Email" value={user?.email ?? "—"} />
          <Info label="Role" value={user?.role ?? "—"} />
          <Info label="Active" value={user?.is_active ? "Yes" : "No"} />
        </div>
      </section>

      <section className="glass rounded-xl p-6">
        <h2 className="font-semibold">API & Session</h2>
        <div className="mt-4 space-y-3">
          <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-background/40 p-3">
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">API Base URL</p>
              <p className="truncate font-mono text-sm">{API_BASE_URL}</p>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                navigator.clipboard?.writeText(API_BASE_URL);
                toast.success("Copied");
              }}
            >
              <Copy className="h-3.5 w-3.5" />
            </Button>
          </div>
          <Info
            label="Session"
            value={hasToken ? "Authenticated — token stored locally" : "No active token"}
          />
        </div>
      </section>

      <section className="glass rounded-xl p-6">
        <h2 className="font-semibold">Appearance</h2>
        <div className="mt-4 flex items-center justify-between">
          <div>
            <p className="text-sm">Theme</p>
            <p className="text-xs text-muted-foreground">Switch between dark and light surfaces.</p>
          </div>
          <Button variant="outline" onClick={toggleTheme} className="gap-2">
            {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {isDark ? "Light mode" : "Dark mode"}
          </Button>
        </div>
      </section>

      <section className="glass rounded-xl p-6">
        <h2 className="font-semibold">Sign out</h2>
        <p className="mt-1 text-sm text-muted-foreground">End your session on this device.</p>
        <Button
          variant="destructive"
          className="mt-4 gap-2"
          onClick={async () => {
            await logout();
            navigate({ to: "/login" });
          }}
        >
          <LogOut className="h-4 w-4" /> Logout
        </Button>
      </section>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-background/40 p-3">
      <p className="text-xs uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm">{value}</p>
    </div>
  );
}
