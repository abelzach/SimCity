"use client";
import { ImpactScores, BaselineMetrics } from "@/lib/types";

interface Props {
  baseline: BaselineMetrics | null;
  impact: ImpactScores | null;
}

const severityColor: Record<string, string> = {
  highly_positive: "text-emerald-600 bg-emerald-50",
  positive: "text-green-600 bg-green-50",
  neutral: "text-gray-600 bg-gray-50",
  negative: "text-orange-600 bg-orange-50",
  highly_negative: "text-red-600 bg-red-50",
};

const sentimentColor: Record<string, string> = {
  positive: "text-emerald-600",
  negative: "text-red-500",
  neutral: "text-gray-500",
  mixed: "text-amber-500",
};

function formatValue(value: number, unit: string): string {
  if (unit === "INR/day") {
    return `₹${(value / 1000).toFixed(0)}K`;
  }
  if (unit === "kg") {
    return value > 10000 ? `${(value / 1000).toFixed(1)}t` : `${value.toFixed(0)}kg`;
  }
  if (unit === "%") {
    return `${(value * 100).toFixed(1)}%`;
  }
  return `${value.toFixed(1)}${unit}`;
}

interface CardProps {
  label: string;
  before: number;
  after: number;
  deltaPct: number;
  unit: string;
  severity: string;
}

function MetricCard({ label, before, after, deltaPct, unit, severity }: CardProps) {
  const isImprovement = deltaPct < 0;
  const arrow = deltaPct < 0 ? "↓" : deltaPct > 0 ? "↑" : "→";
  const deltaColor = isImprovement ? "text-emerald-600" : deltaPct > 0 ? "text-red-500" : "text-gray-500";

  return (
    <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm">
      <div className="text-xs text-gray-500 font-medium mb-2">{label}</div>
      <div className="flex items-end justify-between gap-2">
        <div>
          <div className="text-lg font-bold text-gray-900">{formatValue(after, unit)}</div>
          <div className="text-xs text-gray-400">was {formatValue(before, unit)}</div>
        </div>
        <div className={`text-sm font-bold ${deltaColor} flex items-center gap-0.5`}>
          <span>{arrow}</span>
          <span>{Math.abs(deltaPct).toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
}

export default function ImpactMetrics({ baseline, impact }: Props) {
  if (!baseline) {
    return (
      <div className="text-sm text-gray-400 text-center py-8">
        Run a simulation to see impact metrics
      </div>
    );
  }

  if (!impact) {
    // Show baseline only
    return (
      <div>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Baseline Metrics (Kochi)
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm">
            <div className="text-xs text-gray-500 font-medium mb-1">Avg Congestion</div>
            <div className="text-xl font-bold text-gray-900">
              {(baseline.avg_congestion_ratio * 100).toFixed(1)}%
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm">
            <div className="text-xs text-gray-500 font-medium mb-1">Avg Travel Time</div>
            <div className="text-xl font-bold text-gray-900">
              {baseline.avg_travel_time_min.toFixed(1)} min
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm">
            <div className="text-xs text-gray-500 font-medium mb-1">Daily CO₂</div>
            <div className="text-xl font-bold text-gray-900">
              {(baseline.daily_co2_kg / 1000).toFixed(1)}t
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm">
            <div className="text-xs text-gray-500 font-medium mb-1">Economic Loss</div>
            <div className="text-xl font-bold text-gray-900">
              ₹{(baseline.economic_loss_inr_per_day / 100000).toFixed(1)}L/day
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
        Impact Metrics (Before → After)
      </h2>

      {/* Core metrics grid */}
      <div className="grid grid-cols-2 gap-3">
        <MetricCard
          label={impact.congestion.label}
          before={impact.congestion.before}
          after={impact.congestion.after}
          deltaPct={impact.congestion.delta_pct}
          unit={impact.congestion.unit}
          severity={impact.congestion.severity}
        />
        <MetricCard
          label={impact.travel_time.label}
          before={impact.travel_time.before}
          after={impact.travel_time.after}
          deltaPct={impact.travel_time.delta_pct}
          unit={impact.travel_time.unit}
          severity={impact.travel_time.severity}
        />
        <MetricCard
          label={impact.co2_emissions.label}
          before={impact.co2_emissions.before}
          after={impact.co2_emissions.after}
          deltaPct={impact.co2_emissions.delta_pct}
          unit={impact.co2_emissions.unit}
          severity={impact.co2_emissions.severity}
        />
        <MetricCard
          label={impact.economic_loss.label}
          before={impact.economic_loss.before}
          after={impact.economic_loss.after}
          deltaPct={impact.economic_loss.delta_pct}
          unit={impact.economic_loss.unit}
          severity={impact.economic_loss.severity}
        />
      </div>

      {/* Citizen satisfaction */}
      {impact.citizen_satisfaction?.by_group?.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm">
          <div className="text-xs text-gray-500 font-medium mb-3">Citizen Impact by Group</div>
          <div className="flex flex-col gap-2">
            {impact.citizen_satisfaction.by_group.map((g) => (
              <div key={g.group} className="flex items-center justify-between gap-2">
                <span className="text-xs text-gray-700 truncate flex-1">{g.group}</span>
                <div className="flex items-center gap-2">
                  <div className="w-20 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        g.impact_score > 0
                          ? "bg-emerald-400"
                          : g.impact_score < 0
                          ? "bg-red-400"
                          : "bg-gray-300"
                      }`}
                      style={{ width: `${Math.abs(g.impact_score) * 10}%` }}
                    />
                  </div>
                  <span
                    className={`text-xs font-medium w-8 text-right ${
                      sentimentColor[g.sentiment] || "text-gray-500"
                    }`}
                  >
                    {g.impact_score > 0 ? "+" : ""}
                    {g.impact_score}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
