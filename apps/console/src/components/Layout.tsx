import { NavLink, Outlet } from "react-router-dom";
import {
  Activity,
  ClipboardCheck,
  LayoutDashboard,
  ScrollText,
  Shield,
} from "lucide-react";

const nav = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/reviews", label: "Review Queue", icon: ClipboardCheck },
  { to: "/privacy", label: "Privacy Budget", icon: Shield },
  { to: "/audit", label: "Audit Log", icon: ScrollText },
];

export function Layout() {
  return (
    <div className="flex min-h-screen">
      <aside className="flex w-64 shrink-0 flex-col border-r border-surface-border bg-surface-raised">
        <div className="border-b border-surface-border px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/20 text-accent-glow">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold tracking-tight text-white">CFI-Fed</p>
              <p className="text-xs text-slate-400">Operations Console</p>
            </div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 p-4">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? "bg-accent/15 text-accent-glow shadow-glow"
                    : "text-slate-400 hover:bg-surface-border/30 hover:text-slate-200"
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-surface-border p-4">
          <p className="text-xs leading-relaxed text-slate-500">
            Research prototype — not a production attestation. Raw incident evidence never
            crosses contributor boundaries.
          </p>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <header className="sticky top-0 z-10 border-b border-surface-border bg-surface/80 px-8 py-4 backdrop-blur-md">
          <h1 className="text-lg font-semibold text-white">Federation Operations</h1>
          <p className="text-sm text-slate-400">
            Registry, coordinator, aggregator health and governance
          </p>
        </header>
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
