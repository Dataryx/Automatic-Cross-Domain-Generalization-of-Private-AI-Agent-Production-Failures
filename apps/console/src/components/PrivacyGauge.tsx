import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { PrivacyAccountant } from "../types";

interface PrivacyGaugeProps {
  accountant: PrivacyAccountant;
}

export function PrivacyGauge({ accountant }: PrivacyGaugeProps) {
  const spentPct = (accountant.spent_epsilon / accountant.total_epsilon) * 100;
  const data = [
    { name: "Spent", value: accountant.spent_epsilon, color: "#3b82f6" },
    { name: "Remaining", value: accountant.remaining_epsilon, color: "#334155" },
  ];

  return (
    <div className="card p-6">
      <h3 className="text-sm font-medium text-slate-400">Differential privacy budget (ε)</h3>
      <div className="mt-4 grid gap-6 lg:grid-cols-2">
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={2}
                dataKey="value"
              >
                {data.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: "#1a2332",
                  border: "1px solid #2d3a4f",
                  borderRadius: "8px",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="flex flex-col justify-center space-y-4">
          <div>
            <p className="text-3xl font-semibold text-white">{spentPct.toFixed(1)}%</p>
            <p className="text-sm text-slate-400">of total ε consumed</p>
          </div>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-slate-500">Total ε</dt>
              <dd className="font-mono text-lg text-white">{accountant.total_epsilon}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Spent ε</dt>
              <dd className="font-mono text-lg text-accent-glow">{accountant.spent_epsilon}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Remaining ε</dt>
              <dd className="font-mono text-lg text-success">{accountant.remaining_epsilon}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Releases</dt>
              <dd className="font-mono text-lg text-white">{accountant.release_count}</dd>
            </div>
          </dl>
          <p className="text-xs text-slate-500">
            DP protects tenant influence on aggregates, not poorly generalized CFIs.
          </p>
        </div>
      </div>
    </div>
  );
}
